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
                    except (Exception, AttributeError, RuntimeError):
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
                        except (Exception, AttributeError, RuntimeError):
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
                        except (Exception, AttributeError, RuntimeError):
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
                        except (Exception, AttributeError, RuntimeError):
                            continue

                # Generate the 'codec_description'
                # Format: #index type codec profile [dimensions/rate] [pix_fmt/sample_fmt] [extra]
                stype = stream.type # 'video' or 'audio'
                codec = stream.codec.long_name
                profile = stream.profile if stream.profile else ""

                if stream.codec_tag == 'av01':
                    codec = "AV1 (Alliance for Open Media Video 1)"
                
                # Extract Metadata & Stream Label
                # We look for 'title' but ignore generic 'handler_name'
                meta = stream.metadata or {}
                props['metadata'] = meta
                
                # Logic to find a valid name/title
                title = meta.get('title') or meta.get('NAME') or meta.get('label')
                
                # Ignore handler-related names that aren't useful labels
                handler_names = ['handler', 'handlername', 'videohandler', 'audiohandler', 'soundhandler']
                handler_val = meta.get('handler_name', '').lower().replace(" ", "")
                
                if not title and handler_val not in handler_names:
                    title = meta.get('handler_name')

                props['stream_label'] = title if title else ""
                title = props['stream_label']+" " if props['stream_label'] else ""
                
                if stype == 'video':
                    fps = stream.average_rate
                    fps_str = ""
                    if fps and fps.numerator > 0:
                        if fps.denominator == 1:
                            fps_str = f"{fps.numerator}"
                        else:
                            fps_str = f"{fps.numerator}/{fps.denominator} ({float(fps):.4f})"
                    desc = f"{title}(Video) {codec} {profile}, {stream.width}x{stream.height}, {stream.pix_fmt}, {fps_str} FPS"
                    sdesc = f"V:{stream.name.upper()}"
                
                elif stype == 'audio':
                    sr = stream.sample_rate
                    fmt = stream.format.name if stream.format else ""
                    ch = f"{stream.channels}ch"
                    desc = f"{title}(Audio) {codec}, {ch}, {fmt}, {sr} Hz"
                    sdesc = f"A:{stream.name.upper()}"
                
                else:
                    desc = f"{title}({stype}): {codec}"
                    sdesc = f"{stream.name.upper()}"
                    
                props['codec_description'] = desc.replace("  ", " ").replace(" ,", ",").strip() # Clean double spaces
                props['codec_short_descr'] = sdesc

                self.SourceStreams[stream.index] = props
                print(f"Stream number {props['index']}")
                print("Long description:  "+props['codec_description'])
                print("Short description: "+props['codec_short_descr'])