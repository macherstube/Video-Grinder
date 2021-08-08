# Video-Grinder

Grinds Videos to h265 in a Plex Environment

![Borderlands: The Pre-Sequel - The Grinder in Concordia](https://static.wikia.nocookie.net/borderlands/images/1/10/GrinderPreSequel.jpg/revision/latest/scale-to-width-down/300?cb=20180222220705)

## Why?

You probably have a mess of several old codecs and files with way to huge bitrate. That's ugly.
And takes a lot of storage. And is slow to transcode. Brief calculations show that with using h265 codec 
instead of h264 you can save around 40%.

## Prechecks

We will provide a toolset to run prechecks on your current media.

## Installation

Here we will provide information about how you can install Video-Grinder...

### Running as a Service

... and how you can run it as a service to regularly monitor your library for older formats and 
convert them on a schedule.

## Hardware Recommendation

You can run Video-Grinder on any hardware but be aware that video recoding requires a fast computer/server. 
We tested it on following configurations:

- _Development Environment_
  - OS: Manjaro Linux 5.10.42-1-MANJARO 64bit
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

- Prechecks to get an overview over the existing library
- Conversion of any format that is supported by ffmpeg
- Using following format as a target format: mkv, h265, acc, sub
- Support NVIDIA hardware acceleration (NVENC, NVDEC)
- Support Linux and Windows
- Modes: Bulk/Scheduled/On Change/On Idle
- Update Plex Library (including retaining of metadata and playing history)
- Multitasking (depending on GPU, usually 3 for NVIDIA - check references)

Following functions are ideas that are not yet verified if they are possible:

- Check video quality and verify playability
- Sending reports of transcoding progress

Following functions won't be implemented in the current version:

- AV1 codec support - The reason is that currently there aren't any affordable AV1 hardware encoders on the market.
- Converting multipart files (f.E. DVD Copies)

## References

- https://support.plex.tv/articles/201638786-plex-media-server-url-commands/
- https://developer.nvidia.com/video-encode-and-decode-gpu-support-matrix-new

## Notes

These notes are for later use... You can ignore them. :)

Following PowerShell snippet were used for some testing to simulate how Plex Media Server can handle file changes.

```powershell
cp "[TempPath]\Big Buck Bunny - Sunflower.mkv" "[Path]\Big Buck Bunny - Sunflower_h265.mkv"
Stop-Service -Name "PlexService"
Get-Process | Where-Object {$_.Path -like "*Plex Transcoder.exe*"} | Stop-Process -Force
Remove-Item "[Path]\Big Buck Bunny - Sunflower.mp4"
mv "[Path]\Big Buck Bunny - Sunflower_h265.mkv" "[Path]\Big Buck Bunny - Sunflower.mkv"
Start-Service -Name "PlexService"
Start-Sleep -s 10
Invoke-RestMethod -Uri "http://localhost:32400/library/sections/1/refresh?X-Plex-Token=[Token]"
Start-Sleep -s 5
Invoke-RestMethod -Uri "http://localhost:32400/library/sections/1/analyse?X-Plex-Token=[Token]"
```