from common import *
WORDS=["The","cat","sat","because","it","was","tired"]
class AttentionPaper(Paper):
    def construct(self):
        # 0 title
        t1=Text("Attention Is",font_size=64,color=INK,weight=BOLD); t2=Text("All You Need",font_size=64,color=GOLD,weight=BOLD)
        tt=VGroup(t1,t2).arrange(DOWN,buff=0.3).move_to(UP*2)
        sub=Text("Vaswani et al. · Google · 2017",font_size=30,color=MUTE).next_to(tt,DOWN,buff=0.5)
        ax=Text("arXiv 1706.03762",font_size=26,color=MUTE).next_to(sub,DOWN,buff=0.25)
        self.play(Write(tt),run_time=1.5); self.play(FadeIn(sub),FadeIn(ax))
        self.cap("In 2017, eight Google researchers published a paper with a bold title.")
        self.cap("It introduced the Transformer: the T in ChatGPT.")
        self.clear_stage()
        # 1 the old way: one word at a time
        h=self.heading("Before: one word at a time")
        boxes=VGroup(*[RoundedRectangle(width=1.0,height=0.8,corner_radius=0.12,color=BLUE) for _ in range(6)]).arrange(DOWN,buff=0.45).move_to(UP*1.2)
        labels=VGroup(*[Text(w,font_size=26,color=INK).next_to(b,LEFT,buff=0.5) for w,b in zip(WORDS,boxes)])
        arrows=VGroup(*[Arrow(boxes[i].get_bottom(),boxes[i+1].get_top(),buff=0.05,color=MUTE,stroke_width=3) for i in range(5)])
        self.cap("Older translation models read a sentence like reading through a straw: one word, then the next.",5.5)
        for i in range(6):
            self.play(FadeIn(labels[i]),Create(boxes[i]),*( [GrowArrow(arrows[i-1])] if i else []),run_time=0.45)
        mem=VGroup(*[Dot(b.get_center(),radius=0.18,color=GOLD) for b in boxes])
        self.play(LaggedStart(*[FadeIn(d) for d in mem],lag_ratio=0.25),run_time=1.5)
        self.play(*[mem[i].animate.set_opacity(0.15+0.17*i) for i in range(6)],run_time=1.2)
        self.cap("By the end of a long sentence, the start fades. And each step waits for the last, so it is slow.",5.5)
        self.clear_stage()
        # 2 attention: every word looks at every word
        h=self.heading("Look at everything at once")
        row=VGroup(*[Text(w,font_size=46,color=INK) for w in WORDS]).arrange(DOWN,buff=0.42).move_to(LEFT*1.9+UP*1.2)
        self.play(LaggedStart(*[FadeIn(w,shift=RIGHT*0.3) for w in row],lag_ratio=0.1))
        q=row[4]; self.play(q.animate.set_color(GOLD).scale(1.2))
        self.cap("Attention lets every word look at every other word, all at the same time.",4)
        wts=[0.05,0.62,0.06,0.04,0.02,0.07,0.14]
        lines=VGroup(); bars=VGroup()
        for w,wt in zip(row,wts):
            if w is q: continue
            a=ArcBetweenPoints(q.get_right()+RIGHT*0.1,w.get_right()+RIGHT*0.1,angle=-PI/1.6 if w.get_y()>q.get_y() else PI/1.6)
            a.set_stroke(BLUE,width=1+18*wt,opacity=0.3+wt); lines.add(a)
            b=Rectangle(width=max(0.05,3.2*wt),height=0.32,fill_color=BLUE,fill_opacity=0.8,stroke_width=0).next_to(w,RIGHT,buff=2.2,aligned_edge=LEFT).align_to(RIGHT*0.9,LEFT)
            n=Text(f"{wt:.2f}",font_size=22,color=MUTE).next_to(b,RIGHT,buff=0.12); bars.add(VGroup(b,n))
        self.play(LaggedStart(*[Create(a) for a in lines],lag_ratio=0.1),run_time=2)
        self.cap('The word "it" asks: which words tell me what I mean? It pays most attention to "cat".',5)
        self.play(LaggedStart(*[FadeIn(b,shift=RIGHT*0.2) for b in bars],lag_ratio=0.08))
        self.cap("These attention weights always add up to 1. They are made fresh for every sentence. (Example numbers.)",5)
        self.clear_stage()
        # 3 Q, K, V and the formula
        h=self.heading("Query · Key · Value")
        items=[("Query",GOLD,"what am I looking for?"),("Key",BLUE,"what do I contain?"),("Value",GREEN,"what do I pass on?")]
        rows=VGroup()
        for name,col,desc in items:
            vec=VGroup(*[Square(0.62,fill_color=col,fill_opacity=0.25+0.6*((i*7+len(name))%5)/5,stroke_color=col,stroke_width=1.5) for i in range(5)]).arrange(RIGHT,buff=0.06)
            r=VGroup(Text(name,font_size=42,color=col,weight=BOLD),vec,Text(desc,font_size=32,color=INK)).arrange(DOWN,buff=0.18); rows.add(r)
        rows.arrange(DOWN,buff=0.6).move_to(UP*2.4)
        self.play(LaggedStart(*[FadeIn(r,shift=UP*0.2) for r in rows],lag_ratio=0.3),run_time=2)
        self.cap("Each word makes three lists of numbers: a Query, a Key and a Value.",4)
        self.cap("Match one word's Query against every Key. A good match means: pay attention here.",5)
        f=MathTex(r"\text{Attention}(Q,K,V)=\text{softmax}\!\left(\frac{QK^{\top}}{\sqrt{d_k}}\right)V",color=INK).scale_to_fit_width(8.2).move_to(DOWN*2.6)
        self.play(Write(f),run_time=2.5)
        self.play(Indicate(f[0][14:19],color=GOLD))
        self.cap("Q times K gives the match scores. Dividing by root d_k keeps the numbers from getting too big.",5.5)
        self.cap("Softmax turns scores into weights that add up to 1. Then we mix the Values using those weights.",5.5)
        self.clear_stage()
        # 4 multi-head
        h=self.heading("8 heads, 8 points of view")
        cols=[BLUE,GOLD,GREEN,RED,"#c792ea","#ff9ed8","#9cdcfe","#e5c07b"]
        heads=VGroup()
        for k in range(8):
            fr=RoundedRectangle(width=3.6,height=2.0,corner_radius=0.15,stroke_color=cols[k],stroke_width=2)
            dots=VGroup(*[Dot(radius=0.06,color=INK) for _ in range(7)]).arrange(RIGHT,buff=0.38).move_to(fr.get_center()+DOWN*0.5)
            arcs=VGroup()
            for j in range(3):
                a_,b_=(k*3+j)%7,(k*5+2*j+1)%7
                if a_!=b_: arcs.add(ArcBetweenPoints(dots[a_].get_center(),dots[b_].get_center(),angle=-PI/2).set_stroke(cols[k],width=3))
            heads.add(VGroup(fr,dots,arcs))
        heads.arrange_in_grid(4,2,buff=0.3).move_to(UP*1.2)
        self.play(LaggedStart(*[FadeIn(x) for x in heads],lag_ratio=0.12),run_time=2)
        self.cap("The Transformer runs 8 attentions side by side. Each head can learn a different kind of link between words.",6)
        self.clear_stage()
        # 5 why it won: parallel + results
        h=self.heading("Why it won")
        grid=VGroup(*[Square(0.5,stroke_color=BLUE,stroke_width=2) for _ in range(42)]).arrange_in_grid(6,7,buff=0.1).move_to(UP*3.0)
        self.play(Create(grid),run_time=1)
        self.play(*[s.animate.set_fill(BLUE,0.7) for s in grid],run_time=0.8)
        self.cap("No more waiting in line. All words are processed together, which suits graphics cards perfectly.",5)
        r1=VGroup(Text("English → German",font_size=30,color=MUTE),Text("28.4 BLEU",font_size=52,color=GOLD,weight=BOLD),Text("over 2 points better than the previous best",font_size=24,color=INK)).arrange(DOWN,buff=0.15)
        r2=VGroup(Text("English → French",font_size=30,color=MUTE),Text("41.8 BLEU",font_size=52,color=GOLD,weight=BOLD),Text("trained in 3.5 days on 8 GPUs",font_size=24,color=INK)).arrange(DOWN,buff=0.15)
        VGroup(r1,r2).arrange(DOWN,buff=0.6).move_to(DOWN*1.2)
        self.play(FadeIn(r1,shift=UP*0.2)); self.play(FadeIn(r2,shift=UP*0.2))
        self.cap("It set new records in translation, and trained in a small fraction of the time of the best older models.",6)
        self.clear_stage()
        # 6 legacy
        h=self.heading("What came next",GOLD)
        names=["GPT","BERT","ChatGPT","Claude","AlphaFold 2"]
        tags=VGroup(*[Text(n,font_size=54,color=c) for n,c in zip(names,[BLUE,GREEN,GOLD,RED,"#c792ea"])]).arrange(DOWN,buff=0.45).move_to(UP*1.5)
        self.play(LaggedStart(*[FadeIn(x,shift=UP*0.3) for x in tags],lag_ratio=0.2),run_time=2)
        self.cap("Almost every big AI model today is built on this idea, from chatbots to AlphaFold, which predicts protein shapes.",6)
        self.cap("One idea: let every word look at every other word. Paper: arXiv 1706.03762.",5)
        self.clear_stage(); self.play(FadeOut(self._cap)); self.wait(0.5)
