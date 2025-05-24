from pathlib import Path
import json
import os
import pdb
import copy
# from swebench.harness.log_parsers import MAP_REPO_TO_PARSER
from update_SWE_Bench.log_parsers import MAP_REPO_TO_PARSER


def find_set_difference(set1, set2):
    """
    Finds and prints the differences between two sets.
    - Elements only in set1.
    - Elements only in set2.
    - Elements present in both sets.

    Args:
        set1 (set): The first set.
        set2 (set): The second set.
    """
    # Elements unique to each set
    unique_to_set1 = set1 - set2
    unique_to_set2 = set2 - set1

    # Elements common to both sets
    common_elements = set1 & set2

    # Print unique elements in set1
    if unique_to_set1:
        print("Elements only in set1:", unique_to_set1)
    else:
        print("No unique elements in set1")

    # Print unique elements in set2
    if unique_to_set2:
        print("Elements only in set2:", unique_to_set2)
    else:
        print("No unique elements in set2")

def find_dict_difference(dict1, dict2):
    # in set1 but not set2
    dict_a = copy.deepcopy(dict1)
    dict_b = copy.deepcopy(dict2)
    
    for key in dict_b.keys():
        if dict_b[key] != dict_a[key]:
            print( "There is a difference in " + f"test cases: {key}, gold: {dict_a[key]}, gen: {dict_b[key]}")
  
# log for gold patch
dg = "log4test/gold-366"
dict_g = dict()
for repo in os.listdir(dg):
    if repo.startswith("."):
        continue
    log_fp = os.path.join(dg, repo, "test_output.txt")
    sample_id = str(Path(log_fp).parent.stem)  # e.g. scikit-learn__scikit-learn-12421
    repo = "-".join(sample_id.replace("__", "/").split("-")[:-1])  # e.g. scikit-learn/scikit-learn
    log_parser = MAP_REPO_TO_PARSER[repo]
    if os.path.exists(log_fp):
        with open(log_fp, 'r') as f:
            content = f.read()
        report = log_parser(content)
        dict_g[sample_id] = report
    else:
        print(f"Error in finding {log_fp}")
        continue


suspicious_set = set()
suspicious_list = []

key_suspicious_set = set()
key_suspicious_list = []

# example for testing the intramorphic tesitng algorithm
file_list = ["log4test/20231010_rag_swellama7b"]

# file_list = [
    # "logs/run_evaluation/1209_SampledTest-103_20231010_rag_claude2/20231010_rag_claude2",
    # "logs/run_evaluation/1209_SampledTest-103_20231010_rag_gpt35/20231010_rag_gpt35",
    # "logs/run_evaluation/1209_SampledTest-103_20231010_rag_swellama7b/20231010_rag_swellama7b",
    # "logs/run_evaluation/1209_SampledTest-103_20231010_rag_swellama13b/20231010_rag_swellama13b",
    # "logs/run_evaluation/1209_SampledTest-103_20240402_rag_claude3opus/claude_3_seq2seq",
    # "logs/run_evaluation/1209_SampledTest-103_20240402_rag_gpt4/gpt-4-0125-preview",
    # "logs/run_evaluation/1209_SampledTest-103_20240402_sweagent_claude3opus/claude-3-opus-20240229__swe-bench-lite-test__xml_sys-env_window100-detailed_cmd_format-last_5_history-1_demos__t-0.00__p-0.95__c-4.00__install-1",
    # "logs/run_evaluation/1209_SampledTest-103_20240402_sweagent_claude3opus/claude-3-opus-20240229__swe-bench-test-split-1__xml_sys-env_window100-detailed_cmd_format-last_5_history-1_demos__t-0.00__p-0.95__c-4.00__install-1",
    # "logs/run_evaluation/1209_SampledTest-103_20240402_sweagent_claude3opus/claude-3-opus-20240229__swe-bench-test-split-2__xml_sys-env_window100-detailed_cmd_format-last_5_history-1_demos__t-0.00__p-0.95__c-4.00__install-1",
    # "logs/run_evaluation/1209_SampledTest-103_20240402_sweagent_claude3opus/claude-3-opus-20240229__swe-bench-test-split-3__xml_sys-env_window100-detailed_cmd_format-last_5_history-1_demos__t-0.00__p-0.95__c-4.00__install-1",
    # "logs/run_evaluation/1209_SampledTest-103_20240402_sweagent_claude3opus/claude-3-opus-20240229__swe-bench-test-split-4__xml_sys-env_window100-detailed_cmd_format-last_5_history-1_demos__t-0.00__p-0.95__c-4.00__install-1",
    # "logs/run_evaluation/1209_SampledTest-103_20240402_sweagent_claude3opus/claude-3-opus-20240229__swe-bench-test-split-5__xml_sys-env_window100-detailed_cmd_format-last_5_history-1_demos__t-0.00__p-0.00__c-4.00__install-1",
    # "logs/run_evaluation/1209_SampledTest-103_20240402_sweagent_gpt4/gpt-4-1106-preview__swe-bench-test-split-1__default_sys-env_window100-detailed_cmd_format-last_5_history-1_demos__t-0.00__p-0.95__c-4.00__install-1",
    # "logs/run_evaluation/1209_SampledTest-103_20240402_sweagent_gpt4/gpt-4-1106-preview__swe-bench-test-split-2__default_sys-env_window100-detailed_cmd_format-last_5_history-1_demos__t-0.00__p-0.95__c-4.00__install-1",
    # "logs/run_evaluation/1209_SampledTest-103_20240402_sweagent_gpt4/gpt-4-1106-preview__swe-bench-test-split-3__default_sys-env_window100-detailed_cmd_format-last_5_history-1_demos__t-0.00__p-0.95__c-4.00__install-1",
    # "logs/run_evaluation/1209_SampledTest-103_20240402_sweagent_gpt4/gpt-4-1106-preview__swe-bench-test-split-4__default_sys-env_window100-detailed_cmd_format-last_5_history-1_demos__t-0.00__p-0.95__c-4.00__install-1",
    # "logs/run_evaluation/1209_SampledTest-103_20240402_sweagent_gpt4/gpt-4-1106-preview__swe-bench-test-split-5__default_sys-env_window100-detailed_cmd_format-last_5_history-1_demos__t-0.00__p-0.95__c-4.00__install-1",
    # "logs/run_evaluation/1209_SampledTest-103_20240509_amazon-q-developer-agent-20240430-dev/amazon-q-developer-agent-20240430-dev",
    # "logs/run_evaluation/1209_SampledTest-103_20240615_appmap-navie_gpt4o/appmap-navie_gpt4o",
    # "logs/run_evaluation/1209_SampledTest-103_20240617_factory_code_droid/droid",
    # "logs/run_evaluation/1209_SampledTest-103_20240628_autocoderover-v20240620/autocoderover-v20240620-gpt-4o-2024-05-13",
    # "logs/run_evaluation/1209_SampledTest-103_20240721_amazon-q-developer-agent-20240719-dev/amazon-q-developer-agent-20240719-dev",
    # "logs/run_evaluation/1209_SampledTest-103_20240721_amazon-q-developer-agent-20240719-dev/amazon-q-developer-agent-20240719-dev",
    # "logs/run_evaluation/1209_SampledTest-103_20240728_sweagent_gpt4o/20240728__sweagent__gpt4o",
    # "logs/run_evaluation/1209_SampledTest-103_20240820_epam-ai-run-gpt-4o/epam-ai-run",
    # "logs/run_evaluation/1209_SampledTest-103_20240820_honeycomb/honeycomb",
    # "logs/run_evaluation/1209_SampledTest-103_20240824_gru/20240824_babelcloud_gru",
    # "logs/run_evaluation/1209_SampledTest-103_20240920_solver/2024-09-20-d46be23b958a2bc6138e6fe2260eabcb",
    # "logs/run_evaluation/1209_SampledTest-103_20240924_solver/2024-09-24-f07e921c8e6b0568c5c16ef75283ddba",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-28--12-13",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-28--12-21",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-28--13-06",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-28--14-23",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-28--14-35",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-28--14-51",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-28--15-07",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-28--15-21",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-28--15-38",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-28--15-55",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-28--16-07",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-28--16-28",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--06-19",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--06-29",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--06-41",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--07-01",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--07-19",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--07-42",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--08-31",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--08-48",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--09-22",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--09-42",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--10-03",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--10-20",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--10-37",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--11-01",
    # "logs/run_evaluation/1209_SampledTest-103_20241001_nfactorial/nfactorial-ai-2024-09-30--13-24",
    # "logs/run_evaluation/1209_SampledTest-103_20241002_lingma-agent_lingma-swe-gpt-72b/lingma-swe-gpt-v20240925",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-04--12-28",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-04--13-56",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-04--15-10",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-04--18-19",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-04--19-52",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-04--21-46",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-04--22-31",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-04--23-14",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-05--02-33",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-05--03-19",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-05--03-55",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-05--04-30",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-05--05-14",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-05--05-53",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-05--06-38",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-05--07-42",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-05--08-21",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-05--08-58",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-05--09-39",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-05--14-05",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-05--14-41",
    # "logs/run_evaluation/1209_SampledTest-103_20241007_nfactorial/nfactorial-ai-2024-10-07--03-50",
    # "logs/run_evaluation/1209_SampledTest-103_20241016_composio_swekit/claude-3-5-sonnet",
    # "logs/run_evaluation/1209_SampledTest-103_20241016_epam-ai-run-gpt-4o/epam-ai-run",
    # "logs/run_evaluation/1209_SampledTest-103_20241022_tools_claude-3-5-haiku/tools_claude_3_5_haiku",
    # "logs/run_evaluation/1209_SampledTest-103_20241022_tools_claude-3-5-sonnet-updated/tools_claude_3_5_sonnet_updated",
    # "logs/run_evaluation/1209_SampledTest-103_20241023_emergent/emergent-e1-240920",
    # "logs/run_evaluation/1209_SampledTest-103_20241025_composio_swekit/claude-3-5-sonnet",
    # "logs/run_evaluation/1209_SampledTest-103_20241028_agentless-1.5_gpt4o/agentless",
    # "logs/run_evaluation/1209_SampledTest-103_20241028_solver/2024-10-28-036e3479911e19ccf78c32e206ceba58",
    # "logs/run_evaluation/1209_SampledTest-103_20241029_epam-ai-run-claude-3-5-sonnet/epam-ai-run",
    # "logs/run_evaluation/1209_SampledTest-103_20241029_OpenHands-CodeAct-2.1-sonnet-20241022/claude-3-5-sonnet-20241022_maxiter_100_N_v2.1-no-hint-v0.5-multiaction-run_1",
    # "logs/run_evaluation/1209_SampledTest-103_20241030_nfactorial/nFactorial AI",
    # "logs/run_evaluation/1209_SampledTest-103_20241105_nfactorial/nfactorial",
    # "logs/run_evaluation/1209_SampledTest-103_20241106_navie-2-gpt4o-sonnet/navie2+gpt4o+sonnet3.5",
    # "logs/run_evaluation/1209_SampledTest-103_20241108_autocoderover-v2.0-claude-3-5-sonnet-20241022/autocoderover-v2.0-claude-3-5-sonnet-20241022",
    # "logs/run_evaluation/1209_SampledTest-103_20241108_devlo/devlo",
    # "logs/run_evaluation/1209_SampledTest-103_20241113_nebius-search-open-weight-models-11-24/nebius-qwen-72b-tuned-llama-critic-lookahead-4-candidates-t-0.9-with-selection",
    # "logs/run_evaluation/1209_SampledTest-103_20241120_artemis_agent/artemis-agent",
    # "logs/run_evaluation/1209_SampledTest-103_20241125_enginelabs/enginelabs",
    # "logs/run_evaluation/1209_SampledTest-103_20241125_marscode-agent-dev/20241125_marscode-agent-dev",
    # "logs/run_evaluation/1209_SampledTest-103_20241202_agentless-1.5_claude-3.5-sonnet-20241022/agentless",
    # "logs/run_evaluation/1209_SampledTest-103_20241202_amazon-q-developer-agent-20241202-dev/aws",
# ]



for dm in file_list:
    dict_m = dict()
    if not os.path.exists(dm):
        print(f"Directory {dm} does not exist.")
        continue

    for repo in os.listdir(dm):
        # skip hidden files
        if repo.startswith("."):
            continue
        log_fp = os.path.join(dm, repo, "test_output.txt")
        sample_id = str(Path(log_fp).parent.stem)  # e.g. scikit-learn__scikit-learn-12421
        if not os.path.exists(os.path.join(dm, repo, "report.json")):
            continue
        with open(os.path.join(dm, repo, "report.json"), "r") as f:
            applied_report = json.load(f)
            if_applied = applied_report[sample_id]["patch_successfully_applied"]
        if not if_applied:
            continue
        repo4Parser = "-".join(sample_id.replace("__", "/").split("-")[:-1])  # e.g. scikit-learn/scikit-learn
        # print(repo)
        log_parser = MAP_REPO_TO_PARSER[repo4Parser]
        if os.path.exists(log_fp):
            with open(log_fp, 'r') as f:
                content = f.read()
            report = log_parser(content)
            if report.keys() != dict_g[sample_id].keys():
                print(f"Keys for {sample_id} are different between gold: {dg} and model: {dm}")
                #if need to report key difference, uncomment the following:
                find_set_difference(dict_g[sample_id].keys(), report.keys())
                # pdb.set_trace()
                key_suspicious_set.add(sample_id)
                key_suspicious_list.append(sample_id)
                continue
            if report != dict_g[sample_id]:
                print(f"Report for {sample_id} is different between gold: {dg} and model: {dm}")
                print("here is the differences:")
                # print("gen's report: ", report)
                # print("gold's report: ", dict_g[sample_id])
                # pdb.set_trace()
                find_dict_difference(dict_g[sample_id], report)
                suspicious_set.add(sample_id)
                suspicious_list.append(sample_id)

        else:
            print(f"Error in finding path {log_fp}")
            report = {}
            continue

        dict_m[sample_id] = report


print("length of suspicious set: ", len(suspicious_set))
print("suspicious_set: ", suspicious_set)
print("length of suspicious list: ", len(suspicious_list))
print("suspicious_list: ", suspicious_list)

print("length of key_suspicious set: ", len(key_suspicious_set))
print("key_suspicious_set: ", key_suspicious_set)
print("length of key_suspicious list: ", len(key_suspicious_list))
print("key_suspicious_list: ", key_suspicious_list)

print("total length of suspicious set: ", len(suspicious_set) + len(key_suspicious_set))
print("all suspicious set: ", suspicious_set | key_suspicious_set)
print("total length of suspicious list: ", len(suspicious_list) + len(key_suspicious_list))
print("all suspicious list: ", suspicious_list + key_suspicious_list)
