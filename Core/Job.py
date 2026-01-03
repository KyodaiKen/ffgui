import av
import av.datasets

class Job():
    Name = ""
    SourceFileName = ""
    SourceStreams = {}
    Codec = ""
    DestinationStreams = {}
    DestinationFileName = ""

    def __init__(self, name, srcFileName):
        self.Name = name
        self.SourceFileName = srcFileName

        # Determine SourceStreams using FFMPEG
        with av.open(srcFileName) as media:
            for stream in media.streams:
                props = {}
    
                # Get properties from the Stream object itself
                for attr in dir(stream):
                    if attr.startswith('_') or attr in ['codec_context', 'container']:
                        continue
                    try:
                        val = getattr(stream, attr)
                        if not callable(val):
                            props[attr] = val
                    except (AttributeError, RuntimeError):
                        # Skip unaccessable properties
                        continue

                # Get properties from codec_context
                if stream.codec_context:
                    ctx = stream.codec_context
                    for attr in dir(ctx):
                        if attr.startswith('_'):
                            continue
                        try:
                            val = getattr(ctx, attr)
                            if not callable(val):
                                # Prefixing with 'codec_' to avoid name collisions
                                props[f'codec_context_{attr}'] = val
                        except (AttributeError, RuntimeError):
                            continue

                if stream.codec_context.format:
                    ctx = stream.codec_context.format
                    for attr in dir(ctx):
                        if attr.startswith('_'):
                            continue
                        try:
                            val = getattr(ctx, attr)
                            if not callable(val):
                                # Prefixing with 'codec_' to avoid name collisions
                                props[f'codec_context_format_{attr}'] = val
                        except (AttributeError, RuntimeError):
                            continue

                # Get properties from container
                if stream.container:
                    ctx = stream.container
                    for attr in dir(ctx):
                        if attr.startswith('_') or attr in ['streams']:
                            continue
                        try:
                            val = getattr(ctx, attr)
                            if not callable(val):
                                # Prefixing with 'codec_' to avoid name collisions
                                props[f'container_{attr}'] = val
                        except (AttributeError, RuntimeError):
                            continue

                # Generate the 'codec_description'
                # Format: #index type codec profile [dimensions/rate] [pix_fmt/sample_fmt] [extra]
                stype = stream.type # 'video' or 'audio'
                codec = stream.codec.long_name
                profile = stream.profile if stream.profile else ""

                if stream.codec_tag == 'av01':
                    codec = "AV1 (Alliance for Open Media Video 1)"
                
                if stype == 'video':
                    desc = f"#{stream.index} {stype}: {codec} {profile}, {stream.width}x{stream.height}, {stream.pix_fmt}"
                
                elif stype == 'audio':
                    # Handle audio specifics: rate, format, channels
                    sr = stream.sample_rate
                    fmt = stream.format.name if stream.format else ""
                    ch = f"{stream.channels}ch"
                    desc = f"#{stream.index} {stype}: {codec}, {sr}Hz, {fmt} {ch}"
                
                else:
                    desc = f"#{stream.index} {stype}: {codec}"
                    
                props['codec_description'] = desc.replace("  ", " ").strip() # Clean double spaces

                self.SourceStreams[stream.index] = props
                print(props['codec_description'])
