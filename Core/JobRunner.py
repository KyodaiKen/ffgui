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
        
        # Initialize internal statuses
        for job in self.job_list:
            job['_internal_status'] = JobStatus.PENDING
            job['_progress_percent'] = 0

    def run(self):
        total_jobs = len(self.job_list)
        
        for idx, job in enumerate(self.job_list):
            job['_internal_status'] = JobStatus.RUNNING
            self._execute_job(job, idx, total_jobs)
            job['_internal_status'] = JobStatus.COMPLETED
            job['_progress_percent'] = 100
            
        # Final update
        self.update_callback("All jobs finished.", "100%, ETA 00:00:00", 100)

    def _execute_job(self, job, job_idx, total_jobs):
        # 1. Prepare Command
        # The compiler now returns a list of parts
        cmd_parts = FFmpegCmdCompiler.gen_cmd_from_job(job)
        
        # Add progress and quiet flags
        full_cmd = [self.ffmpeg_bin] + cmd_parts + ["-progress", "-"]
        
        # Handle duration (assumed in job['info']['duration_ms'])
        total_duration_ms = job.get('info', {}).get('duration_ms', 1)
        
        # 2. Launch Process
        # Use DEVNULL for stderr to quieten FFMPEG
        process = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            bufsize=1
        )

        progress_data = {}
        
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            
            if "=" in line:
                key, value = line.strip().split("=", 1)
                progress_data[key] = value
                
                if key == "progress":
                    self._process_update(job, job_idx, total_jobs, progress_data, total_duration_ms)
                    if value == "end":
                        break

        process.wait()

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

    def _process_update(self, job, job_idx, total_count, data, duration_ms):
        # Parse current time
        out_time_ms = int(data.get('out_time_ms', 0)) / 1000
        percentage = min(100, round((out_time_ms / duration_ms) * 100, 1))
        job['_progress_percent'] = percentage

        # Parse speed
        speed_str = data.get('speed', '0x').replace('x', '')
        try:
            speed = float(speed_str)
        except:
            speed = 0.001 # Avoid division by zero

        # Calculate Job ETA
        remaining_ms = duration_ms - out_time_ms
        job_eta_sec = (remaining_ms / 1000) / speed if speed > 0 else 0
        calculated_ETA = self._format_time(job_eta_sec)

        # Assemble individual job string
        fps = data.get('fps', '0')
        bitrate = data.get('bitrate', '0kbits/s')
        total_size = self._format_size(data.get('total_size', 0))
        out_time = data.get('out_time', '00:00:00').split('.')[0]
        dup = data.get('dup_frames', '0')
        
        job_info_str = (f"{percentage}% | FPS: {fps} | {bitrate} | Size: {total_size} | "
                        f"Time: {out_time} | Dup: {dup} | Speed: {speed_str}x | ETA: {calculated_ETA}")

        # Total Progress Calculation
        completed_weight = sum([j.get('_progress_percent', 0) for j in self.job_list])
        total_percentage = round(completed_weight / total_count, 1)
        
        # Total ETA (Current job remaining + following jobs durations)
        future_durations_ms = sum([self.job_list[i].get('info', {}).get('duration_ms', 0) 
                                 for i in range(job_idx + 1, total_count)])
        total_remaining_sec = job_eta_sec + ((future_durations_ms / 1000) / speed if speed > 0 else 0)
        
        total_progress_str = f"{total_percentage}%, ETA {self._format_time(total_remaining_sec)}"

        # Send to UI callback
        self.update_callback(job_info_str, total_progress_str, total_percentage)