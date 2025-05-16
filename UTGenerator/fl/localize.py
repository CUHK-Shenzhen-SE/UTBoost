import argparse
import json
import logging
import re
import os
import pdb

os.environ['OPENAI_API_KEY'] = ''

from datasets import load_dataset
from tqdm import tqdm

from augtest.fl.FL import LLMFL
from augtest.util.preprocess_data import (
    filter_none_python,
    filter_out_test_files,
    get_full_file_paths_and_classes_and_functions,
    show_project_structure,
)
from augtest.util.utils import load_json, load_jsonl
from get_repo_structure.get_repo_structure import (
    clone_repo,
    get_project_structure_from_scratch,
)

# SET THIS IF YOU WANT TO USE THE PREPROCESSED FILES
PROJECT_FILE_LOC = os.environ.get("PROJECT_FILE_LOC", None)


def extractFileFromString(patch_text):
    # Regex pattern to find file paths from the diff --git line
    pattern = r'^diff --git a/(.+?) b/'

    # Find all matches for the pattern
    matches = re.findall(pattern, patch_text, re.MULTILINE)

    # Return the extracted file paths
    return matches

def localize(args):

    swe_bench_data = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
   
    included_set_224 = {'pytest-dev__pytest-5227', 'django__django-11620', 'django__django-14238', 'django__django-16873', 'django__django-13590', 'django__django-11583', 'pytest-dev__pytest-5413', 'django__django-10914', 'django__django-16046', 'django__django-11797', 'django__django-15781', 'pytest-dev__pytest-7432', 'sympy__sympy-15678', 'django__django-11815', 'scikit-learn__scikit-learn-13142', 'django__django-12700', 'sphinx-doc__sphinx-8627', 'matplotlib__matplotlib-26020', 'matplotlib__matplotlib-24149', 'pytest-dev__pytest-11143', 'sympy__sympy-19487', 'sympy__sympy-24066', 'sympy__sympy-17022', 'sympy__sympy-21055', 'django__django-13033', 'django__django-11422', 'django__django-14787', 'django__django-17087', 'scikit-learn__scikit-learn-14092', 'astropy__astropy-6938', 'django__django-15819', 'django__django-14411', 'scikit-learn__scikit-learn-14894', 'sphinx-doc__sphinx-8435', 'django__django-15213', 'django__django-11964', 'sympy__sympy-14774', 'django__django-16400', 'django__django-12983', 'scikit-learn__scikit-learn-13584', 'pytest-dev__pytest-7168', 'django__django-14017', 'django__django-12470', 'psf__requests-2674', 'django__django-10924', 'mwaskom__seaborn-3407', 'pylint-dev__pylint-7114', 'pylint-dev__pylint-6506', 'pylint-dev__pylint-7993', 'scikit-learn__scikit-learn-14087', 'matplotlib__matplotlib-25311', 'scikit-learn__scikit-learn-10297', 'matplotlib__matplotlib-25442', 'matplotlib__matplotlib-23314', 'django__django-16255', 'sympy__sympy-13971', 'django__django-16139', 'django__django-13158', 'sympy__sympy-24213', 'scikit-learn__scikit-learn-25570', 'matplotlib__matplotlib-25332', 'django__django-16595', 'django__django-16527', 'sympy__sympy-14817', 'django__django-14855', 'django__django-12915', 'pytest-dev__pytest-7490', 'matplotlib__matplotlib-22711', 'matplotlib__matplotlib-23562', 'psf__requests-3362', 'sympy__sympy-22005', 'sympy__sympy-13471', 'django__django-15061', 'sympy__sympy-12419', 'django__django-14155', 'sympy__sympy-18189', 'django__django-13660', 'django__django-13315', 'matplotlib__matplotlib-23964', 'django__django-14752', 'django__django-12184', 'django__django-13321', 'scikit-learn__scikit-learn-12471', 'sympy__sympy-22714', 'pydata__xarray-5131', 'sphinx-doc__sphinx-8595', 'sympy__sympy-18532', 'django__django-14580', 'astropy__astropy-14995', 'sympy__sympy-12481', 'sympy__sympy-13031', 'sympy__sympy-24909', 'django__django-11039', 'django__django-15814', 'sympy__sympy-16988', 'django__django-11133', 'django__django-14534', 'sympy__sympy-21614', 'django__django-15902', 'pytest-dev__pytest-11148', 'pytest-dev__pytest-8365', 'matplotlib__matplotlib-24334', 'django__django-15320', 'psf__requests-863', 'scikit-learn__scikit-learn-15535', 'sympy__sympy-16503', 'psf__requests-1963', 'django__django-15347', 'sphinx-doc__sphinx-7975', 'django__django-11049', 'sympy__sympy-15345', 'django__django-13028', 'django__django-12747', 'django__django-12497', 'sympy__sympy-23262', 'sympy__sympy-13480', 'django__django-12284', 'django__django-12125', 'sympy__sympy-20049', 'astropy__astropy-14182', 'sympy__sympy-20154', 'sympy__sympy-15011', 'matplotlib__matplotlib-23987', 'sympy__sympy-17139', 'sympy__sympy-20442', 'sphinx-doc__sphinx-8506', 'django__django-14672', 'django__django-12308', 'pytest-dev__pytest-7373', 'psf__requests-2317', 'django__django-13933', 'sympy__sympy-18621', 'sympy__sympy-14396', 'django__django-15789', 'django__django-15388', 'django__django-11001', 'sympy__sympy-20590', 'django__django-15202', 'sympy__sympy-19007', 'sympy__sympy-23117', 'django__django-11742', 'django__django-13551', 'pylint-dev__pylint-5859', 'sympy__sympy-18835', 'sphinx-doc__sphinx-8721', 'sympy__sympy-13647', 'sphinx-doc__sphinx-8801', 'django__django-11999', 'pylint-dev__pylint-7080', 'django__django-13265', 'mwaskom__seaborn-2848', 'matplotlib__matplotlib-25498', 'sympy__sympy-24152', 'scikit-learn__scikit-learn-25747', 'matplotlib__matplotlib-23476', 'django__django-14999', 'scikit-learn__scikit-learn-13779', 'django__django-12286', 'django__django-14608', 'sympy__sympy-17655', 'django__django-14016', 'django__django-15851', 'django__django-15400', 'scikit-learn__scikit-learn-25500', 'astropy__astropy-14365', 'django__django-15498', 'sphinx-doc__sphinx-8713', 'astropy__astropy-12907', 'django__django-16408', 'sympy__sympy-21847', 'django__django-13757', 'django__django-11099', 'django__django-12453', 'django__django-12113', 'sympy__sympy-18057', 'pydata__xarray-4094', 'pytest-dev__pytest-6116', 'django__django-11283', 'django__django-11179', 'django__django-13658', 'django__django-13401', 'django__django-12708', 'scikit-learn__scikit-learn-15512', 'scikit-learn__scikit-learn-13439', 'django__django-13964', 'matplotlib__matplotlib-23563', 'scikit-learn__scikit-learn-13241', 'sympy__sympy-18698', 'matplotlib__matplotlib-24970', 'django__django-11848', 'pallets__flask-4992', 'sphinx-doc__sphinx-10325', 'scikit-learn__scikit-learn-14983', 'django__django-15790', 'django__django-14382', 'django__django-13447', 'mwaskom__seaborn-3190', 'django__django-12856', 'pytest-dev__pytest-5495', 'django__django-14915', 'django__django-16041', 'matplotlib__matplotlib-26011', 'sympy__sympy-15609', 'mwaskom__seaborn-3010', 'django__django-13768', 'pytest-dev__pytest-5692', 'django__django-17051', 'scikit-learn__scikit-learn-13496', 'scikit-learn__scikit-learn-13497', 'sympy__sympy-21612', 'django__django-13710', 'sphinx-doc__sphinx-10451', 'sympy__sympy-15346', 'django__django-16379', 'sympy__sympy-16792', 'sympy__sympy-21379', 'sympy__sympy-22840', 'matplotlib__matplotlib-23299', 'sympy__sympy-20212', 'django__django-13230', 'scikit-learn__scikit-learn-11281', 'pytest-dev__pytest-7220', 'django__django-13925', 'matplotlib__matplotlib-23913'}
    included_set_408 = {'sphinx-doc__sphinx-10466', 'django__django-13670', 'django__django-11555', 'pylint-dev__pylint-6903', 'django__django-16333', 'django__django-15561', 'pydata__xarray-4075', 'django__django-14349', 'sympy__sympy-15349', 'pytest-dev__pytest-7490', 'django__django-15851', 'django__django-12050', 'django__django-11964', 'sympy__sympy-21379', 'django__django-15375', 'pylint-dev__pylint-6386', 'django__django-15930', 'django__django-16661', 'sympy__sympy-24562', 'matplotlib__matplotlib-24570', 'django__django-16139', 'django__django-12754', 'django__django-11066', 'sympy__sympy-13757', 'sympy__sympy-19040', 'sympy__sympy-19954', 'sympy__sympy-24443', 'sphinx-doc__sphinx-9367', 'django__django-11299', 'django__django-16560', 'django__django-15467', 'sympy__sympy-11618', 'django__django-11532', 'django__django-11999', 'psf__requests-1766', 'django__django-12155', 'psf__requests-1724', 'django__django-11848', 'django__django-16136', 'scikit-learn__scikit-learn-14983', 'scikit-learn__scikit-learn-26323', 'astropy__astropy-14598', 'sympy__sympy-16450', 'django__django-14915', 'django__django-13343', 'django__django-15916', 'scikit-learn__scikit-learn-25232', 'django__django-11477', 'django__django-15037', 'django__django-16662', 'sympy__sympy-17655', 'astropy__astropy-14508', 'django__django-11490', 'django__django-15987', 'astropy__astropy-14995', 'sphinx-doc__sphinx-9258', 'django__django-15380', 'django__django-11603', 'django__django-11749', 'sympy__sympy-16792', 'scikit-learn__scikit-learn-13779', 'django__django-11119', 'django__django-13820', 'sympy__sympy-15599', 'pydata__xarray-6721', 'django__django-14534', 'django__django-12708', 'django__django-15525', 'sympy__sympy-14711', 'sphinx-doc__sphinx-9711', 'django__django-11265', 'sympy__sympy-13551', 'sympy__sympy-23262', 'scikit-learn__scikit-learn-14496', 'sympy__sympy-13877', 'matplotlib__matplotlib-14623', 'django__django-13315', 'django__django-13590', 'django__django-11740', 'pydata__xarray-6744', 'django__django-13410', 'astropy__astropy-7606', 'matplotlib__matplotlib-23412', 'django__django-7530', 'sympy__sympy-22914', 'sphinx-doc__sphinx-8721', 'django__django-11880', 'scikit-learn__scikit-learn-13135', 'scikit-learn__scikit-learn-13142', 'django__django-16569', 'django__django-13516', 'pydata__xarray-2905', 'django__django-16116', 'django__django-16527', 'sympy__sympy-17318', 'pylint-dev__pylint-6528', 'django__django-11292', 'pydata__xarray-4687', 'scikit-learn__scikit-learn-11578', 'django__django-12774', 'django__django-12325', 'django__django-16493', 'sympy__sympy-13798', 'mwaskom__seaborn-3069', 'django__django-16899', 'matplotlib__matplotlib-20488', 'django__django-10973', 'sphinx-doc__sphinx-7454', 'sphinx-doc__sphinx-8035', 'django__django-15499', 'django__django-15569', 'sympy__sympy-18211', 'pylint-dev__pylint-8898', 'django__django-11095', 'django__django-14999', 'django__django-13658', 'scikit-learn__scikit-learn-9288', 'django__django-14500', 'sympy__sympy-12481', 'pydata__xarray-4695', 'sympy__sympy-16766', 'scikit-learn__scikit-learn-12973', 'sphinx-doc__sphinx-9658', 'django__django-17084', 'pydata__xarray-3151', 'pytest-dev__pytest-5262', 'django__django-12262', 'astropy__astropy-14369', 'psf__requests-2931', 'sympy__sympy-19783', 'django__django-14089', 'django__django-15127', 'django__django-14752', 'django__django-13089', 'astropy__astropy-14309', 'sphinx-doc__sphinx-9673', 'django__django-15278', 'django__django-15731', 'django__django-11815', 'sphinx-doc__sphinx-8120', 'django__django-11551', 'django__django-12419', 'sphinx-doc__sphinx-7910', 'sympy__sympy-19495', 'django__django-11790', 'pydata__xarray-6461', 'sympy__sympy-24539', 'pydata__xarray-3095', 'django__django-10880', 'astropy__astropy-8707', 'astropy__astropy-13579', 'django__django-14580', 'django__django-15368', 'django__django-13837', 'matplotlib__matplotlib-25287', 'django__django-13741', 'django__django-13406', 'sympy__sympy-23534', 'django__django-11163', 'scikit-learn__scikit-learn-10908', 'pytest-dev__pytest-5631', 'django__django-12209', 'pytest-dev__pytest-6202', 'pydata__xarray-3677', 'matplotlib__matplotlib-26113', 'sphinx-doc__sphinx-9591', 'django__django-11149', 'matplotlib__matplotlib-25775', 'sympy__sympy-23950', 'sympy__sympy-22456', 'sphinx-doc__sphinx-8459', 'django__django-13933', 'sympy__sympy-19637', 'django__django-15103', 'django__django-12663', 'django__django-11179', 'django__django-15741', 'django__django-15022', 'django__django-15277', 'sympy__sympy-14976', 'sympy__sympy-13480', 'django__django-14053', 'scikit-learn__scikit-learn-12585', 'sympy__sympy-15809', 'django__django-13568', 'matplotlib__matplotlib-25332', 'django__django-13121', 'django__django-13512', 'scikit-learn__scikit-learn-25931', 'django__django-13449', 'django__django-13028', 'django__django-10914', 'django__django-16429', 'django__django-15382', 'matplotlib__matplotlib-13989', 'sympy__sympy-15875', 'psf__requests-2317', 'pydata__xarray-7233', 'django__django-9296', 'django__django-11141', 'django__django-15268', 'matplotlib__matplotlib-24026', 'django__django-14771', 'matplotlib__matplotlib-22865', 'scikit-learn__scikit-learn-10844', 'django__django-16801', 'django__django-16032', 'django__django-14017', 'matplotlib__matplotlib-20676', 'django__django-14238', 'django__django-14404', 'scikit-learn__scikit-learn-13439', 'django__django-12308', 'sympy__sympy-20801', 'pytest-dev__pytest-10081', 'django__django-16595', 'django__django-14122', 'django__django-13023', 'sympy__sympy-13974', 'django__django-16255', 'scikit-learn__scikit-learn-13496', 'django__django-16145', 'psf__requests-1142', 'sympy__sympy-12419', 'sympy__sympy-23824', 'sympy__sympy-22714', 'django__django-15128', 'django__django-14539', 'pydata__xarray-4629', 'django__django-16877', 'django__django-14434', 'sympy__sympy-20590', 'django__django-14493', 'sympy__sympy-24066', 'sympy__sympy-12096', 'sphinx-doc__sphinx-8056', 'scikit-learn__scikit-learn-14087', 'sympy__sympy-13647', 'pytest-dev__pytest-7205', 'django__django-15732', 'sphinx-doc__sphinx-8595', 'django__django-13109', 'sympy__sympy-24213', 'sympy__sympy-15345', 'django__django-12858', 'django__django-12125', 'pytest-dev__pytest-10051', 'astropy__astropy-12907', 'sphinx-doc__sphinx-8593', 'django__django-16315', 'django__django-16819', 'pylint-dev__pylint-7277', 'pytest-dev__pytest-5809', 'astropy__astropy-13236', 'django__django-11276', 'pylint-dev__pylint-4970', 'sphinx-doc__sphinx-9281', 'django__django-11239', 'django__django-13794', 'sympy__sympy-24661', 'astropy__astropy-7166', 'sympy__sympy-19346', 'django__django-14631', 'matplotlib__matplotlib-20859', 'pytest-dev__pytest-7571', 'django__django-12304', 'django__django-12039', 'pydata__xarray-4094', 'scikit-learn__scikit-learn-14894', 'pytest-dev__pytest-6197', 'pytest-dev__pytest-7432', 'django__django-11099', 'sphinx-doc__sphinx-7440', 'matplotlib__matplotlib-24970', 'astropy__astropy-7671', 'sphinx-doc__sphinx-7757', 'scikit-learn__scikit-learn-12682', 'matplotlib__matplotlib-25122', 'sphinx-doc__sphinx-8551', 'django__django-14007', 'sphinx-doc__sphinx-9320', 'astropy__astropy-8872', 'sphinx-doc__sphinx-7889', 'django__django-11211', 'django__django-11951', 'sympy__sympy-20154', 'sympy__sympy-13031', 'django__django-13925', 'sympy__sympy-21847', 'pydata__xarray-4966', 'pydata__xarray-3993', 'django__django-16082', 'django__django-13363', 'django__django-14351', 'pydata__xarray-6599', 'django__django-13810', 'astropy__astropy-14096', 'scikit-learn__scikit-learn-25102', 'django__django-14140', 'pydata__xarray-7393', 'sympy__sympy-18189', 'django__django-16938', 'django__django-16100', 'scikit-learn__scikit-learn-14053', 'django__django-10097', 'matplotlib__matplotlib-22719', 'sphinx-doc__sphinx-10449', 'pydata__xarray-4356', 'sympy__sympy-18763', 'django__django-14559', 'sympy__sympy-17139', 'pytest-dev__pytest-7324', 'scikit-learn__scikit-learn-13124', 'django__django-17087', 'django__django-12193', 'django__django-15814', 'django__django-11333', 'sympy__sympy-14531', 'sympy__sympy-16886', 'django__django-14373', 'sympy__sympy-15017', 'astropy__astropy-14539', 'django__django-13346', 'django__django-14376', 'django__django-11133', 'django__django-16454', 'matplotlib__matplotlib-24149', 'sphinx-doc__sphinx-8475', 'django__django-15695', 'django__django-15161', 'django__django-13821', 'django__django-14787', 'matplotlib__matplotlib-23314', 'django__django-12713', 'django__django-14672', 'django__django-15315', 'django__django-15572', 'sphinx-doc__sphinx-9698', 'matplotlib__matplotlib-23476', 'sphinx-doc__sphinx-10673', 'django__django-13786', 'django__django-13569', 'astropy__astropy-13453', 'sphinx-doc__sphinx-9230', 'django__django-13012', 'sympy__sympy-13878', 'django__django-16901', 'scikit-learn__scikit-learn-14141', 'scikit-learn__scikit-learn-15100', 'django__django-12273', 'django__django-11451', 'scikit-learn__scikit-learn-25747', 'django__django-16612', 'django__django-13033', 'django__django-16642', 'pytest-dev__pytest-7521', 'django__django-13551', 'sympy__sympy-18698', 'sphinx-doc__sphinx-8269', 'django__django-13417', 'matplotlib__matplotlib-20826', 'pylint-dev__pylint-7080', 'django__django-14311', 'pytest-dev__pytest-7982', 'django__django-13279', 'django__django-12143', 'astropy__astropy-7336', 'matplotlib__matplotlib-26342', 'matplotlib__matplotlib-24637', 'scikit-learn__scikit-learn-11310', 'scikit-learn__scikit-learn-25973', 'django__django-16485', 'django__django-11206', 'sphinx-doc__sphinx-10323', 'django__django-17029', 'matplotlib__matplotlib-23299', 'django__django-15104', 'django__django-12276', 'pytest-dev__pytest-7236', 'sphinx-doc__sphinx-7985', 'matplotlib__matplotlib-24627', 'django__django-13809', 'django__django-14855', 'django__django-15863', 'pallets__flask-5014', 'scikit-learn__scikit-learn-10297', 'django__django-13128', 'scikit-learn__scikit-learn-14629', 'django__django-13807', 'sympy__sympy-13615', 'django__django-14608', 'django__django-13158', 'scikit-learn__scikit-learn-13328', 'pydata__xarray-3305', 'psf__requests-5414', 'django__django-14765', 'django__django-12965', 'psf__requests-1921', 'sympy__sympy-13372', 'django__django-13112', 'django__django-13964', 'django__django-12741', 'pytest-dev__pytest-8399', 'scikit-learn__scikit-learn-14710', 'matplotlib__matplotlib-26291', 'matplotlib__matplotlib-25311', 'django__django-13401', 'django__django-13297'}
    included_set = included_set_224
    if args.start_file:
        start_file_locs = load_jsonl(args.start_file)

    for bug in tqdm(swe_bench_data):
        # cnt += 1
        # if cnt > 1:
        #     break
        if bug['instance_id'] not in included_set:
            continue

        if args.target_id is not None:
            if args.target_id != bug["instance_id"]:
                continue

        if PROJECT_FILE_LOC is not None:
            project_file = os.path.join(PROJECT_FILE_LOC, bug["instance_id"] + ".json")
            d = load_json(project_file)
        else:
            # we need to get the project structure directly
            d = get_project_structure_from_scratch(
                bug["repo"], bug["base_commit"], bug["instance_id"], "playground"
            )

        instance_id = d["instance_id"]

        logging.info(f"================ localize {instance_id} ================")

        # pdb.set_trace()
        bench_data = [x for x in swe_bench_data if x["instance_id"] == instance_id][0]
        problem_statement = bench_data["problem_statement"]
        test_patch = bench_data["test_patch"]
        test_patch_files = extractFileFromString(test_patch)
        structure = d["structure"]
        filter_none_python(structure)


        found_files = []
        found_related_locs = []
        found_edit_locs = []

        additional_artifact_loc_file = None
        additional_artifact_loc_related = None
        additional_artifact_loc_edit_location = None
        file_traj, related_loc_traj, edit_loc_traj = {}, {}, {}

        # pdb.set_trace()
        # file level localization
        if args.file_level:
            fl = LLMFL(
                d["instance_id"],
                structure,
                problem_statement,
                test_patch,
                test_patch_files,
                args.model,
                args.backend,
            )
            found_files, additional_artifact_loc_file, file_traj = fl.localize(
                mock=args.mock
            )
        else:
            # assume start_file is provided
            for locs in start_file_locs:
                if locs["instance_id"] == d["instance_id"]:
                    found_files = locs["found_files"]
                    additional_artifact_loc_file = locs["additional_artifact_loc_file"]
                    file_traj = locs["file_traj"]

                    if "found_related_locs" in locs:
                        found_related_locs = locs["found_related_locs"]
                        additional_artifact_loc_related = locs[
                            "additional_artifact_loc_related"
                        ]
                        related_loc_traj = locs["related_loc_traj"]
                    break

        # related class, functions, global var localization
        if args.related_level:
            if len(found_files) != 0:
                pred_files = found_files[: args.top_n]
                fl = LLMFL(
                    d["instance_id"],
                    structure,
                    problem_statement,
                    test_patch,
                    test_patch_files,
                    args.model,
                    args.backend,
                )

                additional_artifact_loc_related = []
                found_related_locs = []
                related_loc_traj = {}

                if args.compress:
                    (
                        found_related_locs,
                        additional_artifact_loc_related,
                        related_loc_traj,
                    ) = fl.localize_function_from_compressed_files(
                        pred_files,
                        mock=args.mock,
                    )
                    additional_artifact_loc_related = [additional_artifact_loc_related]
                else:
                    assert False, "Not implemented yet."

        if args.fine_grain_line_level:
            # Only supports the following args for now

            pred_files = found_files[: args.top_n]
            fl = LLMFL(
                instance_id,
                structure,
                problem_statement,
                test_patch,
                test_patch_files,
                args.model,
                args.backend,
            )
            coarse_found_locs = {}
            for i, pred_file in enumerate(pred_files):
                if len(found_related_locs) > i:
                    coarse_found_locs[pred_file] = found_related_locs[i]
            (
                found_edit_locs,
                additional_artifact_loc_edit_location,
                edit_loc_traj,
            ) = fl.localize_line_from_coarse_function_locs(
                pred_files,
                coarse_found_locs,
                context_window=args.context_window,
                add_space=args.add_space,
                no_line_number=args.no_line_number,
                sticky_scroll=args.sticky_scroll,
                mock=args.mock,
                temperature=args.temperature,
                num_samples=args.num_samples,
            )

            additional_artifact_loc_edit_location = [
                additional_artifact_loc_edit_location
            ]

        with open(args.output_file, "a") as f:
            f.write(
                json.dumps(
                    {
                        "instance_id": d["instance_id"],
                        "found_files": found_files,
                        "additional_artifact_loc_file": additional_artifact_loc_file,
                        "file_traj": file_traj,
                        "found_related_locs": found_related_locs,
                        "additional_artifact_loc_related": additional_artifact_loc_related,
                        "related_loc_traj": related_loc_traj,
                        "found_edit_locs": found_edit_locs,
                        "additional_artifact_loc_edit_location": additional_artifact_loc_edit_location,
                        "edit_loc_traj": edit_loc_traj,
                    }
                )
                + "\n"
            )


def merge(args):
    """Merge predicted locations."""
    start_file_locs = load_jsonl(args.start_file)

    # Dump each location sample.
    for st_id in range(args.num_samples):
        en_id = st_id
        merged_locs = []
        for locs in start_file_locs:
            merged_found_locs = []
            if "found_edit_locs" in locs and len(locs["found_edit_locs"]):
                merged_found_locs = [
                    "\n".join(x) for x in locs["found_edit_locs"][st_id]
                ]
            merged_locs.append({**locs, "found_edit_locs": merged_found_locs})
        with open(
            f"{args.output_folder}/loc_merged_{st_id}-{en_id}_outputs.jsonl", "w"
        ) as f:
            for data in merged_locs:
                f.write(json.dumps(data) + "\n")

    # Pair wise merge
    for st_id in range(0, args.num_samples - 1, 2):
        en_id = st_id + 1
        print(f"Merging sample {st_id} and {en_id}...")
        merged_locs = []
        for locs in start_file_locs:
            merged_found_locs = []
            if "found_edit_locs" in locs and len(locs["found_edit_locs"]):
                merged_found_locs = [
                    "\n".join(x) for x in locs["found_edit_locs"][st_id]
                ]
                for sample_found_locs in locs["found_edit_locs"][st_id + 1 : en_id + 1]:
                    for i, file_found_locs in enumerate(sample_found_locs):
                        if isinstance(file_found_locs, str):
                            merged_found_locs[i] += "\n" + file_found_locs
                        else:
                            merged_found_locs[i] += "\n" + "\n".join(file_found_locs)
            merged_locs.append({**locs, "found_edit_locs": merged_found_locs})
        with open(
            f"{args.output_folder}/loc_merged_{st_id}-{en_id}_outputs.jsonl", "w"
        ) as f:
            for data in merged_locs:
                f.write(json.dumps(data) + "\n")

    ### Merge all
    all_merged_locs = []
    print("Merging all samples...")
    for locs in start_file_locs:
        merged_found_locs = []
        if "found_edit_locs" in locs and len(locs["found_edit_locs"]):
            merged_found_locs = ["\n".join(x) for x in locs["found_edit_locs"][0]]
            for sample_found_locs in locs["found_edit_locs"][1:]:
                for i, file_found_locs in enumerate(sample_found_locs):
                    if isinstance(file_found_locs, str):
                        merged_found_locs[i] += "\n" + file_found_locs
                    else:
                        merged_found_locs[i] += "\n" + "\n".join(file_found_locs)
        all_merged_locs.append({**locs, "found_edit_locs": merged_found_locs})
    with open(f"{args.output_folder}/loc_all_merged_outputs.jsonl", "w") as f:
        for data in all_merged_locs:
            f.write(json.dumps(data) + "\n")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--output_folder", type=str, required=True)
    parser.add_argument("--output_file", type=str, default="loc_outputs.jsonl")
    parser.add_argument(
        "--start_file",
        type=str,
        help="""previous output file to start with to reduce
        the work, should use in combination without --file_level""",
    )
    parser.add_argument("--file_level", action="store_true")
    parser.add_argument("--related_level", action="store_true")
    parser.add_argument("--fine_grain_line_level", action="store_true")
    parser.add_argument("--top_n", type=int, default=3)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--num_samples", type=int, default=1)
    parser.add_argument("--compress", action="store_true")
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--add_space", action="store_true")
    parser.add_argument("--no_line_number", action="store_true")
    parser.add_argument("--sticky_scroll", action="store_true")
    parser.add_argument("--context_window", type=int, default=10)
    parser.add_argument("--target_id", type=str)
    parser.add_argument(
        "--mock", action="store_true", help="Mock run to compute prompt tokens."
    )
    parser.add_argument(
        # "--model", type=str, default="gpt-4o-mini", choices=["gpt-4o-2024-05-13"]
        # "--model", type=str, default="gpt-4o-2024-05-13", choices=["gpt-4o-2024-05-13"]
        "--model", type=str, default="gpt-4o-2024-08-06", choices=["gpt-4o-2024-08-06"]
        # "--model", type=str, default="gpt-4o-2024-05-13", choices=["gpt-4o-2024-05-13"]
    )
    parser.add_argument("--backend", type=str, default="openai", choices=["openai"])

    args = parser.parse_args()

    import os

    args.output_file = os.path.join(args.output_folder, args.output_file)

    assert not os.path.exists(args.output_file), "Output file already exists"

    assert not (
        args.file_level and args.start_file
    ), "Cannot use both file_level and start_file"

    assert not (
        args.file_level and args.fine_grain_line_level and not args.related_level
    ), "Cannot use both file_level and fine_grain_line_level without related_level"

    assert not (
        (not args.file_level) and (not args.start_file)
    ), "Must use either file_level or start_file"

    os.makedirs(args.output_folder, exist_ok=True)

    # write the arguments
    with open(f"{args.output_folder}/args.json", "w") as f:
        json.dump(vars(args), f, indent=4)

    logging.basicConfig(
        filename=f"{args.output_folder}/localize.log",
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    if args.merge:
        merge(args)
    else:
        localize(args)


if __name__ == "__main__":
    main()
