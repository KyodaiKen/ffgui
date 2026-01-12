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
        cmd_parts = FFmpegCmdCompiler.gen_cmd_from_job(job)
        
        # The compiler returns the args; we wrap it with the binary and progress flags
        full_cmd = [self.ffmpeg_bin] + ["-hide_banner"] + cmd_parts
        print(f"Executing: {' '.join(full_cmd)}")
        
        # Determine total duration from stream metadata
        max_duration = 0
        active_streams = [s for s in job.get('sources', {}).get('streams', []) if s.get('active')]
        
        for s in active_streams:
            stream_dur = s.get('duration', 0)
            if stream_dur > max_duration:
                max_duration = stream_dur

        # Use the found duration, or fallback to 1 to avoid division by zero
        total_duration_us = max_duration if max_duration > 0 else 1
        
        # 2. Launch Process
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
            if not line and process.poll() is not None:
                break
            
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
        # 1. Parse current time (Microseconds)
        # If N/A, we use the last percentage we had to avoid jumping back to 0
        raw_us = data.get('out_time_us')
        
        if raw_us == "N/A" or not raw_us:
            # If we are finishing, force 100%. Otherwise, keep last known.
            if data.get('progress') == 'end':
                current_us = duration_us
            else:
                current_us = int((job.get('_progress_percent', 0) / 100.0) * duration_us)
        else:
            current_us = self._get_safe_int(data, 'out_time_us')

        print(f"c:{current_us} t:{duration_us}")

        # 2. Calculate Percentage

        if duration_us > 0:
            percentage = min(100.0, round((current_us / duration_us) * 100, 1))
        else:
            percentage = 100.0 if data.get('progress') == 'end' else 0.0
            
        job['_progress_percent'] = percentage

        # 3. Parse Speed & FPS safely
        speed = self._get_safe_float(data, 'speed', default=0.001)
        fps = data.get('fps', '0')
        speed_str = data.get('speed', '0x')

        # 4. Calculate Job ETA
        remaining_us = max(0, duration_us - current_us)
        job_eta_sec = (remaining_us / 1_000_000) / speed if speed > 0.001 else 0
        calculated_ETA = self._format_time(job_eta_sec)

        # 5. Assemble individual job string
        bitrate = data.get('bitrate', 'N/A')
        total_size = self._format_size(self._get_safe_int(data, 'total_size'))
        # Use 'out_time' string if available, otherwise format our current_us
        out_time_str = data.get('out_time', '00:00:00').split('.')[0]
        if out_time_str == "N/A":
             out_time_str = self._format_time(current_us / 1_000_000)

        job_info_str = (f"{percentage}% | FPS: {fps} | {bitrate} | Size: {total_size} | "
                        f"Time: {out_time_str} | Speed: {speed_str} | ETA: {calculated_ETA}")

        # 6. Total Progress Calculation
        completed_weight = sum([j.get('_progress_percent', 0) for j in self.job_list])
        total_percentage = round(completed_weight / total_count, 1)
        
        # 7. Total ETA Calculation
        future_durations_sec = 0
        for i in range(job_idx + 1, total_count):
            d_ms = 0
            # Look into the new metadata structure we built in JobSetupWindow
            for s in self.job_list[i].get('sources', {}).get('streams', []):
                if s.get('active'):
                    d_ms = s.get('import_metadata', {}).get('duration', 0)
                    break
            future_durations_sec += (d_ms / 1000)

        total_remaining_sec = job_eta_sec + (future_durations_sec / speed if speed > 0.001 else 0)
        total_progress_str = f"{total_percentage}%, Total ETA: {self._format_time(total_remaining_sec)}"

        # Send to UI callback
        self.update_callback(job_info_str, total_progress_str, total_percentage)