import json
import pdb
import os
import json
import pickle
import argparse
# from datasets import load_dataset

def load_jsonl(filepath):
    """
    Load a JSONL file from the given filepath.

    Arguments:
    filepath -- the path to the JSONL file to load

    Returns:
    A list of dictionaries representing the data in each line of the JSONL file.
    """
    with open(filepath, "r") as file:
        return [json.loads(line) for line in file]

def write_jsonl(data, filepath):
    """
    Write data to a JSONL file at the given filepath.

    Arguments:
    data -- a list of dictionaries to write to the JSONL file
    filepath -- the path to the JSONL file to write
    """
    with open(filepath, "w") as file:
        for entry in data:
            file.write(json.dumps(entry) + "\n")
            
def main(args):
    num_input_files = args.num_input_files
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    for i in range(0, num_input_files):
        path = f'{args.input_dir}/output_{i}_processed.jsonl'
        try:
            l = load_jsonl(path)
        except Exception as e:
            print(f"Error loading {path}: {e}")
            continue
        tmp_dict = dict()
        for item in l:
            tmp_dict[ item['instance_id'] ] = item['model_patch']
        json_path = f'{args.output_dir}/output_{i}_processed.json'
        with open(json_path, 'w') as json_file:
            json.dump(tmp_dict, json_file, indent=2)
        
        print(f"Saved dictionary to {json_path}")
        
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', type=str, required=True)
    parser.add_argument('--output_dir', type=str, required=True)
    parser.add_argument('--num_input_files', type=int, required=True)
    args = parser.parse_args()
    main(args)