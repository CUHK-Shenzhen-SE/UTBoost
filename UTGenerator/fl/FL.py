import logging
import re
import pdb
from abc import ABC, abstractmethod

from augtest.repair.repair import construct_topn_file_context
from augtest.util.compress_file import get_skeleton
from augtest.util.postprocess_data import extract_code_blocks, extract_locs_for_files
from augtest.util.preprocess_data import (
    get_full_file_paths_and_classes_and_functions,
    get_repo_files,
    line_wrap_content,
    show_project_structure,
)


class FL(ABC):
    def __init__(self, instance_id, structure, problem_statement, test_patch, test_patch_files, **kwargs):
        self.structure = structure
        self.instance_id = instance_id
        self.problem_statement = problem_statement
        self.test_patch = test_patch
        self.test_patch_files = test_patch_files

    @abstractmethod
    def localize(self, top_n=1, mock=False) -> tuple[list, list, list, any]:
        pass


class LLMFL(FL):
    obtain_relevant_files_prompt = """
You are a test case generator. Please analyze the following GitHub problem description and the provided repository structure. You may modify one or more files to add the test cases.

### GitHub Problem Description ###
{problem_statement}

###

There is an original test patch that is used to verify the fix. You can learn from it to generate new test cases that thoroughly test the fix. You can refer to the files that have been modified in the original test patch. Meanwhile, please check whether the issue can be solved by adding new tests to the existing tests in the original test patch, otherwise, you may need to modify other files.
### Original Test Patch ###
{test_patch}

###

### Files located in the original test patch ###
{test_patch_files} 

###

### Repository Structure ###
{structure}

###

Please only provide the full path and return at most 5 files. the files located in the original test patch should be included and should be at the top of the list.
The returned files should be separated by new lines ordered by most to least important and wrapped with ```
For example:
```
file1.py
file2.py
```
"""

#     obtain_relevant_code_prompt = """
# You are a test case generator. Please analyze the following GitHub problem description and the provided repository structure. Your goal is to identify files and locations that need to be modified to add the test cases to see whether the issue can be solved.

# ### GitHub Problem Description ###
# {problem_statement}

# ###

# There is an original test patch that is used to verify the fix.
# ### Original Test Patch ###
# {test_patch}

# ###

# ### File: {file_name} ###
# {file_content}

# ###

# Please provide either the class, the function name or line numbers that need to be edited.
# ### Example 1:
# ```
# class: MyClass
# ```
# ### Example 2:
# ```
# function: my_function
# ```
# ### Example 3:
# ```
# line: 10
# line: 24
# ```

# Return just the location(s)
# """
#     file_content_template = """
# ### File: {file_name} ###
# {file_content}
# """
    file_content_in_block_template = """
### File: {file_name} ###
```python
{file_content}
```
"""
    obtain_relevant_code_combine_top_n_prompt = """
You are a test case generator. Please review the following GitHub problem description and relevant files, and provide a set of locations that one would need to add test cases and import functions to see whether the issue can be solved.
The locations can be specified as class names, function or method names, or exact line numbers that require modification.

### GitHub Problem Description ###
{problem_statement}

There is an original test patch that is used to verify the fix. You can learn from its files and locations that have been modified, and the functions it imports. 
### Original Test Patch ###
{test_patch}

###

###
{file_contents}

###

Please provide the class name, function or method name, or the exact line numbers that need to be edited to add the test cases and add the necessary imports to see whether the issue can be solved.
### Examples:
```
full_path1/file1.py
line: 10
class: MyClass1
line: 51

full_path2/file2.py
function: MyClass2.my_method
line: 12

full_path3/file3.py
function: my_function
line: 24
line: 156
```

Return just the location(s)
"""
    obtain_relevant_code_combine_top_n_no_line_number_prompt = """
You are a test case generator. Please review the following GitHub problem description and relevant files, and provide a set of locations that one would need to add test cases and import functions to see whether the issue can be solved.
The locations can be specified as class, method, or function names that require modification.

### GitHub Problem Description ###
{problem_statement}

There is an original test patch that is used to verify the fix. You can learn from its files and locations that have been modified. Meanwhile, please check whether the issue can be solved by adding new tests to the existing tests in the original test patch, otherwise, you may need to modify other files.
### Original Test Patch ###
{test_patch}

###

###
{file_contents}

###

Please provide the class, method, or function names that need to be edited.
### Examples:
```
full_path1/file1.py
function: my_function1
class: MyClass1

full_path2/file2.py
function: MyClass2.my_method
class: MyClass3

full_path3/file3.py
function: my_function2
```

Return just the location(s)
"""
#     obtain_relevant_functions_from_compressed_files_prompt = """
# You are a test case generator. Please look through the following GitHub problem description and the skeleton of relevant files.
# Provide a thorough set of locations that one would need to add test cases to see whether the issue can be solved, including directly related areas as well as any potentially related functions and classes.

# ### GitHub Problem Description ###
# {problem_statement}

# There is an original test patch that is used to verify the fix. You can refer to the file, class, function and locations it modified.
# ### Original Test Patch ###
# {test_patch}

# ###

# ###
# {file_contents}

# ###

# Please provide locations as either the class or the function name.
# ### Examples:
# ```
# full_path1/file1.py
# class: MyClass1

# full_path2/file2.py
# function: MyClass2.my_method

# full_path3/file3.py
# function: my_function
# ```

# Return just the location(s)
# """
    obtain_relevant_functions_and_vars_from_compressed_files_prompt_more = """
Please look through the following GitHub Problem Description and the Skeleton of Relevant Files.
Identify all locations that need to be edited to add the test cases and the corresponding import functions to see whether the issue can be solved, including directly related areas as well as any potentially related global variables, functions, and classes.
For each location you provide, either give the name of the class, the name of a method in a class, the name of a function, or the name of a global variable.

### GitHub Problem Description ###
{problem_statement}

There is an original test patch that is used to verify the fix. You can refer to the file, class, function and locations it modified, and especially what functions it imports.
### Original Test Patch ###
{test_patch}

###

### Skeleton of Relevant Files ###
{file_contents}

###

Please provide the complete set of locations as either a class name, a function name, or a variable name.
Note that if you include a class, you do not need to list its specific methods.
You can include either the entire class or don't include the class name and instead include specific methods in the class.
### Examples:
```
full_path1/file1.py
function: my_function_1
class: MyClass1
function: MyClass2.my_method

full_path2/file2.py
variable: my_var
function: MyClass3.my_method

full_path3/file3.py
function: my_function_2
function: my_function_3
function: MyClass4.my_method_1
class: MyClass5
```

Return just the locations.
"""

    def __init__(
        self, instance_id, structure, problem_statement, test_patch, test_patch_files, model_name, backend, **kwargs
    ):
        super().__init__(instance_id, structure, problem_statement, test_patch, test_patch_files)
        self.max_tokens = 300
        self.model_name = model_name
        self.backend = backend

    def _parse_model_return_lines(self, content: str) -> list[str]:
        return content.strip().split("\n")

    def localize(self, top_n=1, mock=False) -> tuple[list, list, list, any]:
        # lazy import, not sure if this is actually better?
        from augtest.util.api_requests import num_tokens_from_messages
        from augtest.util.model import make_model

        found_files = []

        message = self.obtain_relevant_files_prompt.format(
            problem_statement=self.problem_statement,
            test_patch=self.test_patch,
            test_patch_files=self.test_patch_files,
            structure=show_project_structure(self.structure).strip(),
        ).strip()
        # deal with only the test function name
        if 'sensitive' in message:
            message = message.replace('sensitive', 'xxxxxxxxx')
        print(f"prompting with message:\n{message}")
        print("=" * 80)
        if mock:
            traj = {
                "prompt": message,
                "usage": {
                    "prompt_tokens": num_tokens_from_messages(
                        message, "gpt-4o-2024-08-06"
                    ),
                },
            }
            return [], {"raw_output_loc": ""}, traj

        model = make_model(
            model=self.model_name,
            backend=self.backend,
            max_tokens=self.max_tokens,
            temperature=0,
            batch_size=1,
        )
        # pdb.set_trace()
        traj = model.codegen(message, num_samples=1)[0]
        traj["prompt"] = message
        raw_output = traj["response"]
        # pdb.set_trace()
        model_found_files = self._parse_model_return_lines(raw_output)

        files, classes, functions = get_full_file_paths_and_classes_and_functions(
            self.structure
        )

        for file_content in files:
            file = file_content[0]
            if file in model_found_files:
                found_files.append(file)

        # sort based on order of appearance in model_found_files
        found_files = sorted(found_files, key=lambda x: model_found_files.index(x))

        print(raw_output)

        return (
            found_files,
            {"raw_output_files": raw_output},
            traj,
        )

    def localize_function_for_files(
        self, file_names, mock=False
    ) -> tuple[list, dict, dict]:
        from augtest.util.api_requests import num_tokens_from_messages
        from augtest.util.model import make_model

        files, classes, functions = get_full_file_paths_and_classes_and_functions(
            self.structure
        )

        max_num_files = len(file_names)
        while 1:
            # added small fix to prevent too many tokens
            contents = []
            for file_name in file_names[:max_num_files]:
                for file_content in files:
                    if file_content[0] == file_name:
                        content = "\n".join(file_content[1])
                        file_content = line_wrap_content(content)
                        contents.append(
                            self.file_content_template.format(
                                file_name=file_name, file_content=file_content
                            )
                        )
                        break
                else:
                    raise ValueError(f"File {file_name} does not exist.")

            file_contents = "".join(contents)
            if num_tokens_from_messages(file_contents, "gpt-4o-2024-08-06") < 128000:
                break
            else:
                max_num_files -= 1

        message = self.obtain_relevant_code_combine_top_n_prompt.format(
            problem_statement=self.problem_statement,
            test_patch=self.test_patch,
            file_contents=file_contents,
        ).strip()

        # deal with only the test function name
        if 'sensitive' in message:
            message = message.replace('sensitive', 'xxxxxxxxx')

        print(f"prompting with message:\n{message}")
        print("=" * 80)
        if mock:
            traj = {
                "prompt": message,
                "usage": {
                    "prompt_tokens": num_tokens_from_messages(
                        message, "gpt-4o-2024-08-06"
                    ),
                },
            }
            return [], {"raw_output_loc": ""}, traj

        model = make_model(
            model=self.model_name,
            backend=self.backend,
            max_tokens=self.max_tokens,
            temperature=0,
            batch_size=1,
        )
        traj = model.codegen(message, num_samples=1)[0]
        traj["prompt"] = message
        raw_output = traj["response"]

        model_found_locs = extract_code_blocks(raw_output)
        model_found_locs_separated = extract_locs_for_files(
            model_found_locs, file_names
        )

        print(raw_output)

        return model_found_locs_separated, {"raw_output_loc": raw_output}, traj

    def localize_function_from_compressed_files(self, file_names, mock=False):
        from augtest.util.api_requests import num_tokens_from_messages
        from augtest.util.model import make_model

        file_contents = get_repo_files(self.structure, file_names)
        compressed_file_contents = {
            fn: get_skeleton(code) for fn, code in file_contents.items()
        }
        contents = [
            self.file_content_in_block_template.format(file_name=fn, file_content=code)
            for fn, code in compressed_file_contents.items()
        ]
        file_contents = "".join(contents)
        template = (
            self.obtain_relevant_functions_and_vars_from_compressed_files_prompt_more
        )
        message = template.format(
            problem_statement=self.problem_statement, test_patch=self.test_patch, file_contents=file_contents
        )
        
        # deal with only the test function name
        if 'sensitive' in message:
            message = message.replace('sensitive', 'xxxxxxxxx')
            
        
        assert num_tokens_from_messages(message, "gpt-4o-2024-08-06") < 128000
        logging.info(f"prompting with message:\n{message}")
        logging.info("=" * 80)

        if mock:
            traj = {
                "prompt": message,
                "usage": {
                    "prompt_tokens": num_tokens_from_messages(
                        message,
                        self.model_name,
                    ),
                },
            }
            return [], {"raw_output_loc": ""}, traj

        model = make_model(
            model=self.model_name,
            backend=self.backend,
            max_tokens=self.max_tokens,
            temperature=0,
            batch_size=1,
        )
        traj = model.codegen(message, num_samples=1)[0]
        traj["prompt"] = message
        raw_output = traj["response"]
        model_found_locs = extract_code_blocks(raw_output)
        model_found_locs_separated = extract_locs_for_files(
            model_found_locs, file_names
        )

        logging.info(f"==== raw output ====")
        logging.info(raw_output)
        logging.info("=" * 80)
        logging.info(f"==== extracted locs ====")
        for loc in model_found_locs_separated:
            logging.info(loc)
        logging.info("=" * 80)

        print(raw_output)

        return model_found_locs_separated, {"raw_output_loc": raw_output}, traj

    def localize_line_from_coarse_function_locs(
        self,
        file_names,
        coarse_locs,
        context_window: int,
        add_space: bool,
        sticky_scroll: bool,
        no_line_number: bool,
        temperature: float = 0.0,
        num_samples: int = 1,
        mock=False,
    ):
        from augtest.util.api_requests import num_tokens_from_messages
        from augtest.util.model import make_model

        file_contents = get_repo_files(self.structure, file_names)
        topn_content, file_loc_intervals = construct_topn_file_context(
            coarse_locs,
            file_names,
            file_contents,
            self.structure,
            context_window=context_window,
            loc_interval=True,
            add_space=add_space,
            sticky_scroll=sticky_scroll,
            no_line_number=no_line_number,
        )
        if no_line_number:
            template = self.obtain_relevant_code_combine_top_n_no_line_number_prompt
        else:
            template = self.obtain_relevant_code_combine_top_n_prompt
        message = template.format(
            problem_statement=self.problem_statement, test_patch=self.test_patch, file_contents=topn_content
        )
        # deal with only the test function name
        if 'sensitive' in message:
            message = message.replace('sensitive', 'xxxxxxxxx')
        logging.info(f"prompting with message:\n{message}")
        logging.info("=" * 80)
        assert num_tokens_from_messages(message, "gpt-4o-2024-08-06") < 128000
        if mock:
            traj = {
                "prompt": message,
                "usage": {
                    "prompt_tokens": num_tokens_from_messages(
                        message, "gpt-4o-2024-08-06"
                    ),
                },
            }
            return [], {"raw_output_loc": ""}, traj

        model = make_model(
            model=self.model_name,
            backend=self.backend,
            max_tokens=self.max_tokens,
            temperature=temperature,
            batch_size=num_samples,
        )
        raw_trajs = model.codegen(message, num_samples=num_samples)

        # Merge trajectories
        raw_outputs = [raw_traj["response"] for raw_traj in raw_trajs]
        traj = {
            "prompt": message,
            "response": raw_outputs,
            "usage": {  # merge token usage
                "completion_tokens": sum(
                    raw_traj["usage"]["completion_tokens"] for raw_traj in raw_trajs
                ),
                "prompt_tokens": sum(
                    raw_traj["usage"]["prompt_tokens"] for raw_traj in raw_trajs
                ),
            },
        }
        model_found_locs_separated_in_samples = []
        for raw_output in raw_outputs:
            model_found_locs = extract_code_blocks(raw_output)
            model_found_locs_separated = extract_locs_for_files(
                model_found_locs, file_names
            )
            model_found_locs_separated_in_samples.append(model_found_locs_separated)

            logging.info(f"==== raw output ====")
            logging.info(raw_output)
            logging.info("=" * 80)
            print(raw_output)
            print("=" * 80)
            logging.info(f"==== extracted locs ====")
            for loc in model_found_locs_separated:
                logging.info(loc)
            logging.info("=" * 80)
        logging.info("==== Input coarse_locs")
        coarse_info = ""
        for fn, found_locs in coarse_locs.items():
            coarse_info += f"### {fn}\n"
            if isinstance(found_locs, str):
                coarse_info += found_locs + "\n"
            else:
                coarse_info += "\n".join(found_locs) + "\n"
        logging.info("\n" + coarse_info)
        if len(model_found_locs_separated_in_samples) == 1:
            model_found_locs_separated_in_samples = (
                model_found_locs_separated_in_samples[0]
            )

        return (
            model_found_locs_separated_in_samples,
            {"raw_output_loc": raw_outputs},
            traj,
        )
