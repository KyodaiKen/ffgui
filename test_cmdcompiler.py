import argparse
import sys
import os
import traceback
from Models.JobsDataModel import JobsDataModel
from Core.FFmpegCmdCompiler import FFmpegCmdCompiler

def main():
    parser = argparse.ArgumentParser(description="FFmpeg Command Compiler Debugger")
    parser.add_argument("file", help="Path to the jobs YAML file")
    parser.add_argument("--verbose", action="store_true", help="Print extra job info")
    
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    try:
        # 1. Load data via JobsDataModel
        # This returns a list of jobs or a single job dict
        data = JobsDataModel.load_from_file(args.file)
        jobs = data if isinstance(data, list) else [data]

        print(f"--- Debugging {len(jobs)} Jobs ---\n")

        for i, job in enumerate(jobs):
            job_name = job.get('name', f'Job {i}')
            print(f"[{i}] Processing: {job_name}")

            if args.verbose:
                print(f"    - Input Files: {len(job.get('sources', {}).get('files', []))}")
                print(f"    - Total Streams: {len(job.get('sources', {}).get('streams', {}))}")

            # 3. Generate the Command
            try:
                # We add the output filename/path at the end for a complete debug string
                cmd_args = FFmpegCmdCompiler.gen_cmd_from_job(job)
                cmd_str = " ".join(cmd_args)

                full_command = f"ffmpeg {cmd_str}"

                print("\033[92mGenerated Command:\033[0m") # Print in green
                print(f"{full_command}\n")
                print("-" * 40)

            except Exception:
                traceback.print_exc()

    except Exception:
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()