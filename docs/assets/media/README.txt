MuJoCo clips for the website
===========================

Put the nine movement clips in this folder. The block "Nine movements, replayed in a simulated hand"
at the top of the Results section is hidden until at least one clip is here, and shows a tile for
every clip it finds.

File names
----------
Easiest: rename the clips to m1.mp4 ... m9.mp4 in this order.

  m1.mp4  Thumb flexion            m6.mp4  Index pointer
  m2.mp4  Thumb abduction          m7.mp4  Cylindrical grip
  m3.mp4  Index flexion            m8.mp4  Lateral grip
  m4.mp4  Middle flexion           m9.mp4  Tripod grip
  m5.mp4  Ring and little flexion

Or keep your own names and edit the "clips" list near the top of docs/assets/js/data.js so each
"file" matches. The caption under the heading is "clipsCaption" in the same place.

Format
------
H.264 .mp4, no audio needed. Nine clips play at once, so keep each one small: about 720 px wide and
under 3 MB is plenty. To shrink a clip (needs ffmpeg):

  ffmpeg -i in.mp4 -vf scale=720:-2 -an -c:v libx264 -crf 28 -pix_fmt yuv420p -movflags +faststart m1.mp4

GitHub rejects any single file over 100 MB.
