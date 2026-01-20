import os
import subprocess
import time
import math
from Core.FFmpegCmdCompiler import FFmpegCmdCompiler

class JobStatus:
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"

class JobRunner:
    def __init__(self, job_list, ffmpeg_executable_path, update_callback):
        """
        :param job_list: List of job dictionaries
        :param ffmpeg_executable_path: Path to the ffmpeg binary
        :param update_callback: function(job_progress_str, total_progress_str, total_percentage)
        """
        self.job_list = job_list
        self.ffmpeg_bin = ffmpeg_executable_path
        self.update_callback = update_callback
        self.current_job_start_time = 0
        
        # Initialize internal statuses
        for job in self.job_list:
            if '_internal_status' not in job:
                job['_internal_status'] = JobStatus.PENDING
                job['_progress_percent'] = 0

    def run(self):
        total_jobs = len(self.job_list)
        
        for idx, job in enumerate(self.job_list):
            # SKIP ALREADY COMPLETED JOBS
            if job.get('_internal_status') != JobStatus.PENDING:
                pct = round(((idx + 1) / total_jobs) * 100, 1)
                self.update_callback(job, "Skipping completed job...", f"{pct}%", pct)
                continue

            job['_internal_status'] = JobStatus.RUNNING
            # Trigger UI update immediately so the row shows it's starting
            self.update_callback(job, "Starting...", f"Job {idx+1}/{total_jobs}", (idx / total_jobs) * 100)
            
            success = self._execute_job(job, idx, total_jobs)
            
            # Mark final state
            job['_internal_status'] = JobStatus.COMPLETED if success else JobStatus.FAILED
            if success:
                job['_progress_percent'] = 100

            #print(f"Job Status Posted: {job['_internal_status']}")

            # Force an update immediately after the job finishes
            pct = round(((idx + 1) / total_jobs) * 100, 1)
            self.update_callback(job, "Job Finished", f"Batch: {pct}%", pct)
            
        self.update_callback(None, "All jobs finished.", "100%", 100)

    def _execute_job(self, job, job_idx, total_jobs):
        # 1. Prepare Command
        cmd_parts = FFmpegCmdCompiler.gen_cmd_from_job(job)
        
        # The compiler returns the args; we wrap it with the binary and progress flags
        full_cmd = [self.ffmpeg_bin] + ["-hide_banner"] + cmd_parts
        print(f"Executing: {' '.join(full_cmd)}")
        
        # Determine total duration from stream metadata
        max_duration = job.get("total_duration", 0) * 1e+6 #Convert to microseconds

        if max_duration == 0:
            print("WARNING: No duration for progress calculation!")

        # Use the found duration, or fallback to 1 to avoid division by zero
        total_duration_us = max_duration if max_duration > 0 else 1

        full_log = []

        self.current_job_start_time = time.time()

        # 2. Launch Process
        if os.name == 'nt':
            flags = 0x08000000 # CREATE_NO_WINDOW
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Pipe stderr to stdout to see errors in the log
                creationflags=flags,  # Prevent a terminal from opening on Windows
                universal_newlines=True,
                bufsize=1
            )
        else:
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Pipe stderr to stdout to see errors in the log
                universal_newlines=True,
                bufsize=1
            )

        progress_data = {}
        while True:
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None: break
                continue

            full_log.append(line.strip())
            
            # If FFmpeg errors out immediately, it won't have '=' in the line
            if "=" in line:
                parts = line.strip().split("=", 1)
                if len(parts) == 2:
                    key, value = parts
                    progress_data[key] = value
                                        
                    if key == "progress":
                        self._process_update(job, job_idx, total_jobs, progress_data, total_duration_us)
                        if value == "end":
                            break
            else:
                # Log non-progress lines (errors/warnings) to console for debugging
                if line.strip():
                    print(f"FFmpeg: {line.strip()}")

        process.wait()

        # CHECK EXIT CODE
        if process.returncode != 0:
            # Save the last 50 lines of the log to the job data for the UI to show
            # This prevents memory bloat while giving enough context for errors
            error_context = "\n".join(full_log[-50:])
            job['_error_msg'] = f"FFmpeg exited with code {process.returncode}\n\nLast output:\n{error_context}"
            return False
            
        return True

    def _format_size(self, bytes_str):
        try:
            bytes_val = int(bytes_str)
            if bytes_val < 1024 * 1024:
                return f"{bytes_val / 1024:.1f} KB"
            elif bytes_val < 1024**3:
                return f"{bytes_val / (1024**2):.1f} MB"
            else:
                return f"{bytes_val / (1024**3):.2f} GB"
        except: return "0 B"

    def _format_time(self, seconds):
        if seconds < 0 or math.isinf(seconds): return "00:00:00"
        return time.strftime('%H:%M:%S', time.gmtime(seconds))

    def _get_safe_int(self, data, key, default=0):
        """Extracts integer from FFmpeg data, handling 'N/A' and invalid strings."""
        val = data.get(key, str(default))
        if val == "N/A" or not val:
            return default
        try:
            return int(val)
        except ValueError:
            return default

    def _get_safe_float(self, data, key, default=0.0):
        """Extracts float from FFmpeg data (like speed), handling 'N/A' and 'x' suffixes."""
        val = data.get(key, str(default)).replace('x', '').strip()
        if val == "N/A" or not val:
            return default
        try:
            return float(val)
        except ValueError:
            return default

    def _process_update(self, job, job_idx, total_count, data, duration_us):
        # 1. Parse current time and percentage (Keep your logic)
        raw_us = self._get_safe_int(data, 'out_time_us')
        current_us = raw_us if raw_us > 0 else int((job.get('_progress_percent', 0) / 100.0) * duration_us)
        
        if duration_us > 0:
            percentage = min(100.0, round((current_us / duration_us) * 100, 1))
        else:
            percentage = 100.0 if data.get('progress') == 'end' else 0.0
        job['_progress_percent'] = percentage

        # 2. Calculate Real Velocity (Media seconds processed / Real seconds elapsed)
        elapsed_real_sec = time.time() - self.current_job_start_time
        current_media_sec = current_us / 1_000_000
        
        # Avoid division by zero: calculate velocity
        # If we just started, use FFmpeg's reported speed as a fallback
        reported_speed = self._get_safe_float(data, 'speed', default=0.001)
        velocity = current_media_sec / elapsed_real_sec if elapsed_real_sec > 0.5 else reported_speed

        # 3. Job ETA
        remaining_job_media_sec = max(0, (duration_us / 1_000_000) - current_media_sec)
        job_eta_sec = remaining_job_media_sec / velocity if velocity > 0.01 else 0
        
        # 4. Total Batch ETA
        # Calculate remaining media seconds for ALL future jobs
        future_media_sec = 0
        for i in range(job_idx + 1, total_count):
            # Use the total_duration field we standardized in previous steps
            future_media_sec += self.job_list[i].get('total_duration', 0)

        total_remaining_media_sec = remaining_job_media_sec + future_media_sec
        batch_eta_sec = total_remaining_media_sec / velocity if velocity > 0.01 else 0

        # 5. UI Strings
        fps = data.get('fps', '0')
        speed_str = data.get('speed', '0x')
        bitrate = data.get('bitrate', 'N/A')
        total_size = self._format_size(self._get_safe_int(data, 'total_size'))
        out_time_str = data.get('out_time', '00:00:00').split('.')[0]

        job_info_str = (f"{percentage}% | FPS: {fps} | {bitrate} | Size: {total_size} | "
                        f"Time: {out_time_str} | Speed: {speed_str} | ETA: {self._format_time(job_eta_sec)}")

        completed_weight = sum([j.get('_progress_percent', 0) for j in self.job_list])
        total_percentage = round(completed_weight / total_count, 1)
        
        total_progress_str = f"{total_percentage}%, Total ETA: {self._format_time(batch_eta_sec)}"

        self.update_callback(job, job_info_str, total_progress_str, total_percentage)