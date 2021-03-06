# Video-Grinder

Grinds videos to h265 in a plex environment

![Borderlands: The Pre-Sequel - The Grinder in Concordia](https://static.wikia.nocookie.net/borderlands/images/1/10/GrinderPreSequel.jpg/revision/latest/scale-to-width-down/300?cb=20180222220705)

## Why?

You probably have a mess of several old codecs and files with way to huge bitrate. That's ugly.
And takes a lot of storage. And is slow to transcode. Brief calculations show that with using h265 codec 
instead of h264 you can save around 40%.

## Prechecks #WIP

We will provide a toolset to run prechecks on your current media.

## Installation #WIP

Here we will provide information about how you can install Video-Grinder...

### Running as a Service #WIP

... and how you can run it as a service to regularly monitor your library for older formats and 
convert them on a schedule.

## Hardware Recommendation

You can run Video-Grinder on any hardware but be aware that video recoding requires a fast computer/server. 
We tested it on following configurations:

- _Development Environment_
  - OS: Manjaro Linux 21.1.0 (5.10.42-1-MANJARO 64bit)
  - CPU: AMD Ryzen 9 4900HS (8C/16T @ 3GHz)
  - GPU: NVIDIA RTX 2060 Max-Q
  - Memory: 16 GB DDR4-3200
  - Storage: Western Digital WDC PC SN530 NVMe 1TB
- _Productive Environment_
  - OS: Windows 10 Pro 21H1 64bit
  - CPU: Intel Core i9-9900K (8C/16T @ 3.6GHz)
  - GPU: NVIDIA GeForce GTX 1080 Ti 
  - Memory: 32 GB DDR4-2666
  - Storage: Samsung SSD 970 EVO NVMe 1TB 

## Considerations

Video-Grinder is build to convert regular video files (such as .mp4, .avi, .mov) to a .mkv file containing 
h265 videostreams(s) and ACC audiostream(s). It will also include existing subtitle stream(s) and trying 
to add standalone subtitle files to the container. 

Following functions will be implemented:

- [ ] Prechecks to get an overview over the existing library
- [x] Conversion of any format that is supported by ffmpeg
- [x] Using following format as a target format: mkv, h265, acc, sub incl. multiple Channels
- [x] Support NVIDIA hardware acceleration (NVENC, NVDEC)
- [x] Support Linux and Windows
- [x] Parameter to schedule/time everything right
- [x] Update Plex Library (including retaining of metadata and playing history)
- [x] Multitasking (depending on GPU, usually 3 for NVIDIA - check references)

Following functions are ideas that are not yet verified if they are possible:

- Check video quality and verify playability
- Sending reports of transcoding progress
- recognize and crop black bars 

Following functions won't be implemented in the current version:

- AV1 codec support - The reason is that currently there aren't any affordable AV1 hardware encoders on the market.
- Converting multipart files (f.E. DVD Copies)

## Tipps

- Because of lack of h265 support don't use browser to playback anymore. Have a look at: 
  - https://knapsu.eu/plex/
  - https://www.plex.tv/de/media-server-downloads/#plex-app
  - https://aur.archlinux.org/packages/plex-media-player/

## References

- https://support.plex.tv/articles/201638786-plex-media-server-url-commands/
- https://developer.nvidia.com/video-encode-and-decode-gpu-support-matrix-new
