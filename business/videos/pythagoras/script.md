# Pythagorean theorem videos (original animation, no copied footage)

Both are vertical 1080x1920, about 35 seconds, text on screen. No voice yet: a voice can be added later from this narration.

## Video 1: Squares on the sides (35 s)
Narration: A right triangle has one square corner. Here the sides are 3, 4 and 5. Build a square on each short side: 9 little squares and 16. Now build one on the long side: 25. The two small squares add up to the big one: 9 plus 16 is 25. In letters, a squared plus b squared equals c squared, where c is the long side. It works for every right triangle. Try 5, 12, 13: 25 plus 144 is 169.

## Video 2: Proof by sliding four triangles (33 s)
Narration: Here is a proof you can see. Four identical right triangles fit inside a big square. The gap in the middle is a square on the long side, c squared. Now slide the same four triangles. The big square does not change. Two squares are left, one on each short side, a squared and b squared. The gap is the same area both times, so c squared equals a squared plus b squared.

## Video 3: Real life, a ladder and a square corner (33 s)
Narration: Where does a squared plus b squared equals c squared help? A 2.5 metre ladder has its foot 0.7 metres from the wall. How high does it reach? The wall, the ground and the ladder make a right triangle, and the ladder is the long side. 0.7 squared plus h squared equals 2.5 squared. That is 0.49 plus h squared equals 6.25, so h squared is 5.76, and h is 2.4 metres. Builders use it too: mark 3 metres along one wall and 4 along the other. If the marks are 5 metres apart, the corner is square. For a real ladder, follow the maker's instructions.

## Caption ideas
- The Pythagorean theorem in 35 seconds. a² + b² = c². #maths #pythagoras #geometry #learnontiktok
- A proof with no algebra: slide four triangles. #mathproof #geometry

## Checks (done / not done)
- Done (video 3): 0.7² + 2.4² = 0.49 + 5.76 = 6.25 = 2.5², so the ladder numbers are exact. The foot-to-height ratio gives an angle near 74 degrees, close to the usual safe ladder angle. The video does not claim any safety rule and tells viewers to follow the maker's instructions.
- Not verified (video 3): the builders' 3-4-5 corner check is a well-known trade practice; I did not look up a source.
- Done: the 3-4-5 numbers (9 + 16 = 25) and 5-12-13 (25 + 144 = 169) are correct.
- Done: the second video uses a = 3, b = 4 in a 7 x 7 square; the gap is 25 before and 9 + 16 after. Area check: 49 - 4 x 6 = 25 = 9 + 16.
- Not verified: "about 2,500 years ago" is a common round figure for Pythagoras's era; the theorem was also known earlier in other places. If you want to be careful, drop the sentence.
- Pythagoras and the theorem are public domain. The drawings and animation here are original.

## Rebuild
node render.js A OUTDIR 24 35   (then ffmpeg -framerate 24 -i OUTDIR/f%05d.jpg ...)
node render.js B OUTDIR 24 33
