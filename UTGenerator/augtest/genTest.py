import pdb
import argparse
import copy
import json
import logging
import re
import os
from difflib import unified_diff
from dotenv import load_dotenv
from datasets import load_dataset
from tqdm import tqdm

from UTGenerator.util.api_requests import (
    create_chatgpt_config,
    num_tokens_from_messages,
    request_chatgpt_engine,
)
from UTGenerator.util.model import make_model
from UTGenerator.util.postprocess_data import (
    check_code_differ_by_just_empty_lines,
    check_syntax,
    extract_python_blocks,
    fake_git_repo,
    lint_code,
    parse_diff_edit_commands,
    parse_edit_commands,
    remove_empty_lines,
    split_edit_multifile_commands,
)
from UTGenerator.util.preprocess_data import (
    get_full_file_paths_and_classes_and_functions,
    get_repo_structure,
    line_wrap_content,
    transfer_arb_locs_to_locs,
)
from UTGenerator.util.utils import load_jsonl

import Levenshtein

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")
os.environ['OPENAI_API_KEY'] = api_key

def find_most_different_code_block(target_code, code_blocks):
    # find max diff
    max_diff = -1
    most_different_code = None
    
    # calculate max distance
    for code in code_blocks:
        diff = Levenshtein.distance(target_code, code)
        if diff > max_diff:
            max_diff = diff    
            most_different_code = code
        if diff >= max(len(target_code), len(code))//5:
            most_different_code = code
            return most_different_code
            
    return most_different_code

def extract_added_imports(test_patch):
    added_imports = []
    lines = test_patch.splitlines()

    # Regex pattern to match Python import statements
    import_pattern = re.compile(r'^\+from\s+[\w\.]+\s+import\s+[\w,\s\(\)]+')

    for line in lines:
        # Check if the line is an added import line
        if import_pattern.match(line):
            # Clean the "+" at the beginning of the line
            added_imports.append(line[1:].strip())

    return added_imports

def extract_added_lines(diff_text):
    added_lines = []
    for line in diff_text.splitlines():
        # Skip diff metadata lines
        if line.startswith(('diff ', 'index ', '---', '+++', '@@')):
            continue
        # Lines that have been added start with '+'
        elif line.startswith('+') and not line.startswith('+++'):
            # Remove the '+' sign but keep the leading spaces
            added_lines.append(line[1:])
    return added_lines

edit_relevant_file_instruction = """
Below are some code segments, each from a relevant file. One or more of these files may be edited to add the test cases.
Please generate the test cases to see whether the issue can be solved, do not remember to import the functions before you use them.
"""
edit_relevant_file_with_scope_instruction = """
Below are some code segments, each from a relevant file. One or more of these files may be edited to add the test cases.
In the file below, "..." refers to some less relevant content being omited for brebity.
"""
with_scope_explanation = """
Note that "..." refers to some omited content that is not actually in the files. Your *SEARCH/REPLACE* edit must not contain such "...".
"""
edit_relevant_file_with_suspicious_loc_instruction = """
Below are some code segments, each from a relevant file. One or more of these files may be edited to add the test cases. Some suspicious locations are provided for closer inspection.
"""
edit_prompt_combine_topn = """
We are currently generating test cases for the following issue within our repository. Here is the issue text:
--- BEGIN ISSUE ---
{problem_statement}
--- END ISSUE ---

There is an original test patch that is used to verify the fix. You can learn from it to generate new test cases that thoroughly test the fix.
--- Original Test Patch ---
```
{test_patch}
```
--- END Original Test Patch ---

{edit_relevant_file_instruction}
--- BEGIN FILE ---
```
{content}
```
--- END FILE ---

Please generate `edit_file` commands to fix the issue.

The `edit_file` command takes four arguments:

edit_file(filename: str, start: int, end: int, content: str) -> None:
    Edit a file. It replaces lines `start` through `end` (inclusive) with the given text `content` in the open file.
    Args:
    filename: str: The full file name to edit.
    start: int: The start line number. Must satisfy start >= 1.
    end: int: The end line number. Must satisfy start <= end <= number of lines in the file.
    content: str: The content to replace the lines with.

Please note that THE `edit_file` FUNCTION REQUIRES PROPER INDENTATION. If you would like to add the line '        print(x)', you must fully write that out, with all those spaces before the code!
Wrap the `edit_file` command in blocks ```python...```.
"""

find_diffrence_between_two_code_blocks = """
Here are two code blocks. Please find the difference between them. We need to generate the test cases to see whether the issue can be solved. You should return the information of the difference, so it can be used to generate the test cases.
--- BEGIN CODE BLOCK 1 ---
{code_block_1}
--- END CODE BLOCK 1 ---

--- BEGIN CODE BLOCK 2 ---
{code_block_2}
--- END CODE BLOCK 2 ---
"""

edit_prompt_combine_topn_cot = """
We are currently generating test cases for the following issue within our repository. Here is the issue text:
--- BEGIN ISSUE ---
{problem_statement}
--- END ISSUE ---

There is an original test patch that is used to verify the fix. You can learn from it to generate new test cases that thoroughly test the fix.
--- Original Test Patch ---
```
{test_patch}
```
--- END Original Test Patch ---

{edit_relevant_file_instruction}
--- BEGIN FILE ---
```
{content}
```
--- END FILE ---

Please first generate the test cases to see whether the issue can be solved.

The `edit_file` command takes four arguments:

edit_file(filename: str, start: int, end: int, content: str) -> None:
    Edit a file. It replaces lines `start` through `end` (inclusive) with the given text `content` in the open file.
    Args:
    filename: str: The full file name to edit.
    start: int: The start line number. Must satisfy start >= 1.
    end: int: The end line number. Must satisfy start <= end <= number of lines in the file.
    content: str: The content to replace the lines with.

Please note that THE `edit_file` FUNCTION REQUIRES PROPER INDENTATION. If you would like to add the line '        print(x)', you must fully write that out, with all those spaces before the code!
Wrap the `edit_file` command in blocks ```python...```.
"""

# This is the active 
edit_prompt_combine_topn_cot_diff = """
We are currently adding test cases for verifying whether the following issue is resolved. Here is the issue text:
--- BEGIN ISSUE ---
{problem_statement}
--- END ISSUE ---

There is an original test patch that is used to verify the fix. 
--- Original Test Patch ---
```
{test_patch}
```
--- END Original Test Patch ---
Here are some guidelines:
1. You should first analyze whether the original test patch conforms to the issue. If the original test patch cannot thoroughly test the fix, generate new test cases to cover more aspects of the fix.
2. Feel free to add more test functions to thoroughly test the fix. Do not remove original test cases.
3. If any required import for the test cases is missing, add it to the file. If it's already present, do not duplicate the import. Make sure to import any necessary packages, modules, or functions before using them in the test cases.
4. You should be aware that some issues describe the incorrect behavior of the code, while some describe the correct behavior of the code. If the issue describes the incorrect behavior, please generate the test cases that expose the issue. If the issue describes the correct behavior, please generate the test cases that the correct behavior can be verified.
5. For assertion failures, you should generate the test cases that can reproduce the assertion failure.

There is a list of imports that are used in the original test patch. You should import them in the test case if you want to use some functions in the original test patch. Or if you want to add new functions, you should also import the functions you need.
--- Added Imports ---
```
{added_imports}
```
--- END Added Imports ---

{edit_relevant_file_instruction}
--- BEGIN FILE ---
```
{content}
```
--- END FILE ---

Your mission is to generate the test cases to see whether the issue can be solved, and check the related original function are not affected by the fix. Try to generate the cases to thoroughly test the fix. Do not remove the original function (we add test cases, but not subtract test cases or function).
Please first localize the places to add the cases along with import functions based on the issue statement, and then generate *SEARCH/REPLACE* edits to add the test cases. You should generate *SEARCH/REPLACE* edits for everywhere you want to edit. 

Every *SEARCH/REPLACE* edit must use this format:
1. The file path
2. The start of search block: <<<<<<< SEARCH
3. A contiguous chunk of lines to search for in the existing source code
4. The dividing line: =======
5. The lines to replace into the source code
6. The end of the replace block: >>>>>>> REPLACE

Here is an example:

```python
### mathweb/flask/app.py
<<<<<<< SEARCH
from flask import Flask
=======
import math
from flask import Flask
>>>>>>> REPLACE
```

Please note that the *SEARCH/REPLACE* edit REQUIRES PROPER INDENTATION. If you would like to add the line '        print(x)', you must fully write that out, with all those spaces before the code!
Wrap the *SEARCH/REPLACE* edit in blocks ```python...```.
"""


def _post_process_multifile_repair(
    raw_output: str,
    file_contents: dict[str, str],
    file_loc_intervals: dict[str, list],
    diff_format=False,
):
    # pdb.set_trace()
    edit_multifile_commands = extract_python_blocks(raw_output)
    edited_file = ""
    new_content = ""
    try:
        file_to_commands = split_edit_multifile_commands(
            edit_multifile_commands, diff_format=diff_format
        )
        logging.info("=== file_to_commands: ===")
        logging.info(json.dumps(file_to_commands, indent=2))
        # Let's only edit the first file in the edit commands.
        edited_file_key = next(iter(file_to_commands.keys()))
        logging.info(f"=== edited_file: {edited_file_key} ===")
        edit_commands = file_to_commands[edited_file_key]
        logging.info("=== edit_commands: ===")
        for c in edit_commands:
            logging.info(c)
            logging.info("\n" + "-" * 40)
        edited_file = eval(edited_file_key)  # convert '"file.py"' to 'file.py'
        content = file_contents[edited_file]
        if diff_format:
            new_content = parse_diff_edit_commands(
                edit_commands, content, file_loc_intervals[edited_file]
            )
        else:
            new_content = parse_edit_commands(edit_commands, content)
    except Exception as e:
        logging.error(e)
        return edited_file, new_content

    diff = list(
        unified_diff(
            content.split("\n"),
            new_content.split("\n"),
            fromfile=edited_file,
            tofile=edited_file,
            lineterm="",
        )
    )

    logging.info(f"extracted patch:")
    logging.info("\n".join(diff))
    print("\n".join(diff))
    return edited_file, new_content


def construct_topn_file_context(
    file_to_locs,
    pred_files,
    file_contents,
    structure,
    context_window: int,
    loc_interval: bool = True,
    fine_grain_loc_only: bool = False,
    add_space: bool = False,
    sticky_scroll: bool = False,
    no_line_number: bool = True,
):
    """Concatenate provided locations to form a context.

    loc: {"file_name_1": ["loc_str_1"], ...}
    """
    file_loc_intervals = dict()
    topn_content = ""

    for pred_file, locs in file_to_locs.items():
        content = file_contents[pred_file]
        line_locs, context_intervals = transfer_arb_locs_to_locs(
            locs,
            structure,
            pred_file,
            context_window,
            loc_interval,
            fine_grain_loc_only,
            file_content=file_contents[pred_file] if pred_file in file_contents else "",
        )

        if len(line_locs) > 0:
            # Note that if no location is predicted, we exclude this file.
            file_loc_content = line_wrap_content(
                content,
                context_intervals,
                add_space=add_space,
                no_line_number=no_line_number,
                sticky_scroll=sticky_scroll,
            )
            topn_content += f"### {pred_file}\n{file_loc_content}\n\n\n"
            file_loc_intervals[pred_file] = context_intervals

    return topn_content, file_loc_intervals


def repair(args):
    logging.basicConfig(
        filename=f"{args.output_folder}/repair.log",
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # write the arguments
    with open(f"{args.output_folder}/args.json", "w") as f:
        json.dump(vars(args), f, indent=4)
        
    swe_bench_data = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    # swe_bench_data = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")

    locs = load_jsonl(args.loc_file)

    if os.path.exists(args.output_file):
        prev_o = load_jsonl(args.output_file)
    else:
        prev_o = []

    # make copy of loc in output_folder
    with open(f"{args.output_folder}/used_locs.jsonl", "w") as f:
        for loc in locs:
            f.write(json.dumps(loc) + "\n")

    for loc in tqdm(locs):
        instance_id = loc["instance_id"]
        
        # if instance_id != 'sympy__sympy-22714':
        #     continue
        found = False
        for o in prev_o:
            if o["instance_id"] == instance_id:
                found = True
                break

        if found:
            logging.info(f"skipping {instance_id} since patch already generated")
            continue

        logging.info(f"================ repairing {instance_id} ================")

        if len(loc["found_files"]) == 0:
            with open(args.output_file, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "instance_id": instance_id,
                            "raw_output": [""],
                            "try_count": [0],
                            "all_generations": [[]],
                            "traj": [],
                            "prev_content": [[]],
                            "file_names": [[]],
                        }
                    )
                    + "\n"
                )

            logging.info(f"skipped since no files were localized")
            continue

        pred_files = loc["found_files"][: args.top_n]

        # grab buggy problem issue description and structure data

        bench_data = [x for x in swe_bench_data if x["instance_id"] == instance_id][0]
        problem_statement = bench_data["problem_statement"]
        test_patch = bench_data["test_patch"]
        gold_patch = bench_data["patch"]
        # for lite
        # gen_patch_list = lite_gen_patches_dict[instance_id]
        # for verified
        # gen_patch_list = verified_gen_patches_dict[instance_id]
        # get the most different generated patch
        # gen_patch = find_most_different_code_block(gold_patch, gen_patch_list)
        # pdb.set_trace()
        added_imports = extract_added_imports(test_patch)
        test_patch = extract_added_lines(bench_data["test_patch"]) # this is for removing the + sign to feed in the final prompt
        structure = get_repo_structure(
            instance_id, bench_data["repo"], bench_data["base_commit"], "playground"
        )
        # max_tries = 3
        # tries = 0
        # while structure is None and tries < max_tries:
        #     time.sleep(1)
        #     structure = get_repo_structure(
        #         instance_id, bench_data["repo"], bench_data["base_commit"], "playground"
        #     )
        #     tries += 1
        files, _, _ = get_full_file_paths_and_classes_and_functions(structure)

        raw_outputs, counts, all_generations, traj, prev_contents, file_names = (
            [],
            [],
            [],
            [],
            [],
            [],
        )

        raw_output = ""
        new_content = ""
        topn_content = ""
        # Construct file contents
        file_contents = dict()
        for i, pred_file in enumerate(pred_files):
            content = None

            for file_content in files:
                if file_content[0] == pred_file:
                    content = "\n".join(file_content[1])
                    file_contents[pred_file] = content
                    break

            assert content is not None, f"{pred_file} file not found"
        # Construct top-n file context
        file_to_edit_locs = dict()
        # import pdb
        # pdb.set_trace()
        for i, pred_file in enumerate(pred_files):
            if "found_edit_locs" in loc and len(loc["found_edit_locs"]) > i:
                file_to_edit_locs[pred_file] = loc["found_edit_locs"][i]

        # pdb.set_trace()
        topn_content, file_loc_intervals = construct_topn_file_context(
            file_to_edit_locs,
            pred_files,
            file_contents,
            structure,
            context_window=args.context_window,
            loc_interval=args.loc_interval,
            fine_grain_loc_only=args.fine_grain_loc_only,
            add_space=args.add_space,
            no_line_number=args.diff_format,
            sticky_scroll=args.sticky_scroll,
        )

        if topn_content.strip() == "":
            with open(args.output_file, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "instance_id": instance_id,
                            "raw_output": [""],
                            "try_count": [0],
                            "all_generations": [[]],
                            "traj": [],
                            "prev_content": [[]],
                            "file_names": [[]],
                        }
                    )
                    + "\n"
                )

            logging.info(f"skipped since no files were localized")
            continue

        # Construct prompt.
        # Note that we assume there's no feedback, and we always use the same prompt in each turn.
        if args.cot and args.diff_format:
            prompt_template = edit_prompt_combine_topn_cot_diff
        elif args.cot:
            prompt_template = edit_prompt_combine_topn_cot
        else:
            prompt_template = edit_prompt_combine_topn

        file_instruction = edit_relevant_file_instruction

        message = prompt_template.format(
            edit_relevant_file_instruction=file_instruction,
            problem_statement=problem_statement,
            added_imports=added_imports,
            # gold_patch=gold_patch,
            # coding_agent_patch=gen_patch,
            test_patch=test_patch,
            content=topn_content.rstrip(),  # remove trailing newlines
        ).strip()
        # pdb.set_trace()

        logging.info(f"prompting with message:\n{message}")

        sample_responses = []
        # Using early stopping will cost more since the input tokens will be charged multiple times.
        # For now we disable it.
        assert args.stop_at_n_unique_valid_samples == -1
        # get greedy sample
        model = make_model(
            model=args.model,
            backend=args.backend,
            # max_tokens=1024,
            # max_tokens=10000,
            max_tokens=4096,
            temperature=0,
            batch_size=1,
        )
        if args.skip_greedy:
            greedy_traj = {
                "response": "",
                "usage": {
                    "completion_tokens": 0,
                    "prompt_tokens": 0,
                },
            }
        else:
            if args.mock:
                greedy_traj = {
                    "response": "",
                    "usage": {
                        "prompt_tokens": num_tokens_from_messages(message, args.model),
                    },
                }
            else:
                greedy_traj = model.codegen(message, num_samples=1)[0]
        sample_responses.append(greedy_traj)
        # get temperature samples
        model = make_model(
            model=args.model,
            backend=args.backend,
            # max_tokens=1024,
            # max_tokens=10000,
            max_tokens=4096,
            temperature=0.99,
            # temperature=2.0,
            batch_size=args.max_samples - 1,  # minus the 1 greedy sample
        )

        if args.mock:
            first_traj = {
                "response": "",
                "usage": {
                    "prompt_tokens": num_tokens_from_messages(message, args.model),
                },
            }
            later_traj = {
                "response": "",
                "usage": {"prompt_tokens": 0},
            }
            if args.max_samples - 1:
                sample_trajs = [first_traj] + [later_traj] * (args.max_samples - 2)
            else:
                sample_trajs = []
        else:
            if args.max_samples - 1:
                sample_trajs = model.codegen(message, num_samples=args.max_samples - 1)
            else:
                sample_trajs = []

        sample_responses.extend(sample_trajs)

        count = 0
        while count < args.max_samples:
            print(f"trying the {count + 1}-th sample ...")
            ret = sample_responses[count]
            count += 1
            traj.append(
                {
                    **ret,
                    "prompt": message,
                }
            )

            if args.mock:
                continue
            raw_output = ret["response"]
            logging.info(f"raw output:\n{raw_output}")
            all_generations.append(raw_output)

            edited_file, new_content = _post_process_multifile_repair(
                raw_output,
                file_contents,
                file_loc_intervals,
                diff_format=args.diff_format,
            )

            if new_content == "":
                prev_contents.append("")
                file_names.append("")
            else:
                prev_content = file_contents[edited_file]
                prev_contents.append(prev_content)
                file_names.append(edited_file)

        counts.append(count)
        raw_outputs.append(raw_output)
        all_generations = [all_generations]
        prev_contents = [prev_contents]
        file_names = [file_names]

        with open(args.output_file, "a") as f:
            f.write(
                json.dumps(
                    {
                        "instance_id": instance_id,
                        "raw_output": raw_outputs,
                        "all_generations": all_generations,
                        "try_count": counts,
                        "traj": traj,
                        "prev_content": prev_contents,
                        "file_names": file_names,
                    }
                )
                + "\n"
            )


def post_process_raw_output(raw_output_text, file_contents, file_loc_intervals, args):
    git_diffs = ""
    raw_git_diffs = ""
    lint_success = False
    content = ""
    try:
        edited_file, new_content = _post_process_multifile_repair(
            raw_output_text,
            file_contents,
            file_loc_intervals,
            diff_format=args.diff_format,
        )
        if edited_file in file_contents:
            content = file_contents[edited_file]

            git_diff = fake_git_repo("playground", edited_file, content, new_content)

            raw_git_diffs += "\n" + git_diff.replace(
                "\ No newline at end of file\n", ""
            )

            syntax_success = check_syntax(new_content)
            lint_success, prev_errors, errors = lint_code(
                "playground", "test.py", new_content, file_contents[edited_file]
            )

            differ_by_empty_lines = check_code_differ_by_just_empty_lines(
                new_content, file_contents[edited_file]
            )

            print(lint_success, prev_errors, errors, differ_by_empty_lines)

            if syntax_success and not differ_by_empty_lines:
                git_diffs = raw_git_diffs
            else:
                git_diffs = ""  # no need to evaluate
        else:
            diff = list(
                unified_diff(
                    content.split("\n"),
                    new_content.split("\n"),
                    fromfile=edited_file,
                    tofile=edited_file,
                    lineterm="",
                )
            )
            print("Failed parsing diff!")
            print("\n".join(diff))
    except Exception as e:
        print(raw_output_text)
        print(e)

    return git_diffs, raw_git_diffs, content


def post_process_repair(args):
    """
    apply some diff formatting.
    """
    raw_outputs = load_jsonl(args.raw_output_file)
    locs = load_jsonl(args.loc_file)

    # pdb.set_trace()

    for raw_output in raw_outputs:
        instance_id = raw_output["instance_id"]

        if raw_output["raw_output"] == "":
            with open(args.output_file, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "model_name_or_path": "agentless",
                            "instance_id": instance_id,
                            "model_patch": "",
                        }
                    )
                    + "\n"
                )
            continue

        if args.select_id == -1:
            # Use the last generation
            assert False, "not implemented for now"
        else:
            # Use the indexed generation
            generation_idx = args.select_id
            try:
                raw_output_text = raw_output["all_generations"][0][generation_idx]
                original_file_content = raw_output["prev_content"][0][generation_idx]
                pred_file = raw_output["file_names"][0][generation_idx]

                pred_files = [loc for loc in locs if loc["instance_id"] == instance_id][
                    0
                ]["found_files"][: args.top_n]

                git_diffs = ""
                raw_git_diffs = ""
                if isinstance(raw_output["raw_output"], str):
                    # for backward compatibility
                    raw_output["raw_output"] = [raw_output["raw_output"]]

                file_contents = {pred_file: original_file_content}

                file_loc_intervals = dict()

                loc = [loc for loc in locs if loc["instance_id"] == instance_id][0]

                for i, tmp_pred_file in enumerate(pred_files):
                    if tmp_pred_file != pred_file:
                        continue
                    if "found_edit_locs" in loc and len(loc["found_edit_locs"]) > i:
                        line_locs, context_intervals = transfer_arb_locs_to_locs(
                            loc["found_edit_locs"][i],
                            None,
                            loc["found_files"][i],
                            args.context_window,
                            args.loc_interval,
                            args.fine_grain_loc_only,
                            file_content=file_contents[pred_file]
                            if pred_file in file_contents
                            else "",
                        )
                    else:
                        line_locs, context_intervals = [], []  # default values.

                    file_loc_intervals[pred_file] = context_intervals
            except:
                raw_output_text = ""

        if raw_output_text:
            git_diffs, raw_git_diffs, content = post_process_raw_output(
                raw_output_text, file_contents, file_loc_intervals, args
            )
        else:
            git_diffs = ""
            raw_git_diffs = ""
            content = ""

        with open(args.output_file, "a") as f:
            f.write(
                json.dumps(
                    {
                        "model_name_or_path": "agentless",
                        "instance_id": instance_id,
                        "model_patch": git_diffs.lstrip(),
                        "raw_model_patch": raw_git_diffs.lstrip(),
                        "original_file_content": content,
                    }
                )
                + "\n"
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loc_file", type=str, required=True)
    parser.add_argument("--top_n", type=int, default=1)
    parser.add_argument("--loc_interval", action="store_true")
    parser.add_argument("--context_window", type=int, default=10)
    parser.add_argument(
        "--stop_at_n_unique_valid_samples",
        type=int,
        default=-1,
        help="Early stop when we get N unique valid samples, set to -1 if don't want to do early stopping.",
    )
    parser.add_argument("--gen_and_process", action="store_true")
    parser.add_argument("--max_samples", type=int, default=20, help="Sampling budget.")
    parser.add_argument(
        "--select_id",
        type=int,
        default=-1,
        help="Index the selected samples during post-processing.",
    )
    parser.add_argument(
        # "--model", type=str, default="gpt-4o-2024-05-13", choices=["gpt-4o-2024-05-13"]
        "--model", type=str, default="gpt-4o-2024-08-06", choices=["gpt-4o-2024-08-06"]
    )
    parser.add_argument("--backend", type=str, default="openai", choices=["openai"])
    parser.add_argument("--output_folder", type=str, required=True)
    parser.add_argument(
        "--only_correct", action="store_true"
    )  # only work on correct loc files (saves time)
    parser.add_argument("--post_process", action="store_true")
    parser.add_argument("--add_space", action="store_true")
    parser.add_argument("--cot", action="store_true")
    parser.add_argument("--fine_grain_loc_only", action="store_true")
    parser.add_argument("--diff_format", action="store_true")
    parser.add_argument("--skip_greedy", action="store_true")
    parser.add_argument("--sticky_scroll", action="store_true")
    parser.add_argument(
        "--mock", action="store_true", help="Mock run to compute prompt tokens."
    )

    args = parser.parse_args()

    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)

    args.output_file = os.path.join(args.output_folder, "output.jsonl")

    if args.post_process:
        args.raw_output_file = args.output_file
        if args.select_id == -1:
            args.output_file = args.raw_output_file.replace(
                ".jsonl", "_processed.jsonl"
            )
        else:
            args.output_file = args.raw_output_file.replace(
                ".jsonl", f"_{args.select_id}_processed.jsonl"
            )
        post_process_repair(args)
    elif args.gen_and_process:
        repair(args)
        args.raw_output_file = args.output_file
        for i in range(args.max_samples):
            args.output_file = args.raw_output_file.replace(
                ".jsonl", f"_{i}_processed.jsonl"
            )
            args.select_id = i
            post_process_repair(args)
    else:
        repair(args)


if __name__ == "__main__":
    main()
