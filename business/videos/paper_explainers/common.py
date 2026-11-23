# Shared look for "paper in 2 minutes" videos: vertical 1080x1920, dark ground, captions carry the narration.
from manim import *
import textwrap
config.pixel_width=1080; config.pixel_height=1920; config.frame_width=9; config.frame_height=16; config.frame_rate=30
BG="#0f1420"; INK="#e8e3d8"; BLUE="#58c4dd"; GOLD="#ffb347"; GREEN="#83c167"; RED="#fc6255"; MUTE="#8a93a6"
class Paper(Scene):
    def setup(self):
        self.camera.background_color=BG; self._cap=None
    def cap(self,text,secs=None):
        """Narration caption at the bottom. Holds for about 2.6 words per second unless secs is given."""
        lines="\n".join(textwrap.wrap(text,30))
        c=Text(lines,font_size=34,color=INK,line_spacing=0.9).move_to(DOWN*5.9)
        if c.width>8.4: c.scale_to_fit_width(8.4)
        box=BackgroundRectangle(c,color=BG,fill_opacity=0.85,buff=0.2); g=VGroup(box,c)
        if self._cap: self.play(FadeOut(self._cap,run_time=0.25),FadeIn(g,run_time=0.35))
        else: self.play(FadeIn(g,run_time=0.35))
        self._cap=g; self.wait(secs if secs else max(1.8,len(text.split())/2.6))
    def clear_stage(self,keep=()):
        objs=[m for m in self.mobjects if m not in keep]
        if objs: self.play(*[FadeOut(m) for m in objs],run_time=0.5)
        self._cap=None
    def heading(self,s,color=GOLD):
        h=Text(s,font_size=44,color=color,weight=BOLD).move_to(UP*6.6)
        if h.width>8.4: h.scale_to_fit_width(8.4)
        self.play(FadeIn(h,shift=DOWN*0.2),run_time=0.5); return h
