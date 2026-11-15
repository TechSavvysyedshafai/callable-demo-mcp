setSegments([
 {c:'One cell becomes *two identical cells*.',d:3.4,hook:1},
 {c:'How? Four phases: *P-M-A-T*.',d:3.4,hook:1},
 {c:'*Prophase*',d:1.8,hook:1},
 {c:'Chromatin condenses into *chromosomes*.',d:3.4},
 {c:'The *nuclear envelope* and *nucleolus* disappear.',d:3.8},
 {c:'*Metaphase*',d:1.8,hook:1},
 {c:'Chromosomes line up at the *equator*…',d:3.2},
 {c:'…attached to *spindle fibres* at their *kinetochores*.',d:3.8},
 {c:'*Anaphase*',d:1.8,hook:1},
 {c:'Centromeres split, and the *chromatids* are pulled to opposite poles.',d:4.8},
 {c:'*Telophase*',d:1.8,hook:1},
 {c:'Chromosomes decondense, and the *nuclear envelope* forms again.',d:4.4},
 {c:'Then *cytokinesis* divides the cytoplasm.',d:3.6},
 {c:'Result: *two identical daughter cells*.',d:3.4},
 {c:'Remember *PMAT*: Prophase, Metaphase, Anaphase, Telophase.',d:5.0},
]);
header('BIOLOGY IN 50 SECONDS · CLASS 11','Mitosis in 4 Phases');
const letters=['P','M','A','T'].map((l,k)=>txt(l,{x:216+k*96,y:220,'text-anchor':'middle','font-size':76,'font-weight':800,fill:'#ddd3c4'}));
const CX=360,CY=600;
const cell=dia(el('g',{}));const eS=[el('ellipse',{fill:'none',stroke:'#c98b5a','stroke-width':10},cell),el('ellipse',{fill:'none',stroke:'#c98b5a','stroke-width':10},cell)];
const eF=[el('ellipse',{fill:'#fbe9d7'},cell),el('ellipse',{fill:'#fbe9d7'},cell)];
const plate=el('line',{x1:110,x2:610,y1:CY,y2:CY,stroke:'#b9a58c','stroke-width':3,'stroke-dasharray':'10 10'});
const plateT=txt('equator',{x:116,y:CY-12,'font-size':19,fill:'#9a8670','font-weight':600});
const nuc=dia(el('circle',{cx:CX,cy:CY,r:175,fill:'#f5dcc4',stroke:'#a8714a','stroke-width':5,'stroke-dasharray':'14 8'}));
const nucl=dia(el('circle',{cx:410,cy:545,r:28,fill:'#8e5a3a'}));
const nucT=txt('nucleolus',{x:446,y:520,'font-size':18,fill:'#8e5a3a','font-weight':600});
function squig(cx,cy,seed,col,parent){let d=`M${cx-60},${cy}`;for(let k=1;k<=12;k++)d+=` L${cx-60+k*10},${cy+Math.sin(k*1.7+seed)*14}`;return el('path',{d,fill:'none',stroke:col,'stroke-width':4,'stroke-linecap':'round',opacity:.8},parent)}
const chromatin=dia(el('g',{}));[[300,540,1,'#e0663a'],[420,630,2,'#e8a07a'],[320,670,3,'#3b82c4'],[400,560,4,'#86b6e0']].forEach(a=>squig(...a,chromatin));
const daughterChrom=[dia(el('g',{})),dia(el('g',{}))];[[0,430],[1,770]].forEach(([k,y])=>{[[-40,-25,1,'#e0663a'],[30,-15,2,'#e8a07a'],[-30,25,3,'#3b82c4'],[35,22,4,'#86b6e0']].forEach(([dx,dy,s,c])=>{const p=squig(CX+dx,y+dy,s,c,daughterChrom[k]);p.setAttribute('transform',`translate(${CX+dx},${y+dy}) scale(.55) translate(${-CX-dx},${-y-dy})`)})});
const dn=[dia(el('circle',{cx:CX,cy:430,r:95,fill:'none',stroke:'#a8714a','stroke-width':5,'stroke-dasharray':'12 7'})),dia(el('circle',{cx:CX,cy:770,r:95,fill:'none',stroke:'#a8714a','stroke-width':5,'stroke-dasharray':'12 7'}))];
const fib=dia(el('g',{}));const fibers=[];for(let k=0;k<8;k++)fibers.push(el('line',{stroke:'#7d8a99','stroke-width':3,opacity:.8},fib));
const polar=[el('line',{stroke:'#b8c1cc','stroke-width':2},fib),el('line',{stroke:'#b8c1cc','stroke-width':2},fib)];
const cent=[0,1].map(()=>{const g=dia(el('g',{}));el('rect',{x:-14,y:-5,width:28,height:10,rx:3,fill:'#5b6b7d'},g);el('rect',{x:-5,y:-14,width:10,height:28,rx:3,fill:'#5b6b7d'},g);return g});
const COL=[['#e0663a',96],['#e8a07a',96],['#3b82c4',68],['#86b6e0',68]];
const start=[[300,545,0.6],[425,625,-0.8],[315,665,1.9],[410,540,2.6]];
const chroms=COL.map(([c,L],k)=>{const g=dia(el('g',{}));const sis=[0,1].map(j=>{const s=el('g',{},g);el('rect',{x:-L/2,y:-9,width:L,height:18,rx:9,fill:c,stroke:'#00000030','stroke-width':2},s);
 el('circle',{cx:-8,cy:-1,r:4.5,fill:'#fff'},s);el('circle',{cx:8,cy:-1,r:4.5,fill:'#fff'},s);el('circle',{cx:-8,cy:0,r:2.2,fill:'#222'},s);el('circle',{cx:8,cy:0,r:2.2,fill:'#222'},s);return s});
 const cm=el('circle',{r:7,fill:'#2b2b2b'},g);return{g,sis,cm,L}});
const kin=txt('kinetochore',{x:0,y:0,'font-size':19,'font-weight':600,fill:'#2b2b2b'});
const masc=dia(makeMascot());finishOverlay();
const S=k=>STARTS[k];
function seek(t){caption(t);const i=segAt(t),u=segU(i,t);
 const ph=i<2?-1:i<5?0:i<8?1:i<10?2:3;
 letters.forEach((l,k)=>{let on=(k==ph);if(i==1)on=segU(1,t)*4.5>k+1;if(i==14)on=segU(14,t)*5>k+0.3;l.setAttribute('fill',on?'#e8803f':(i>=13||k<ph)?'#c9b9a3':'#ddd3c4')});
 // cell division
 const ck=ease(u*(i==12))+(i>12?1:0);
 [[CY,430,-1],[CY,770,1]].forEach(([a,b],k)=>{const cy=lerp(a,b,ck),ry=lerp(320,180,ck),rx=lerp(270,215,ck);set(eS[k],{cx:CX,cy,rx,ry});set(eF[k],{cx:CX,cy,rx:rx-5,ry:ry-5})});
 // nucleus
 const nE=i<4?1:i==4?1-ease(u/.8):0;nuc.setAttribute('opacity',nE);nucl.setAttribute('opacity',nE);nucT.setAttribute('opacity',i<4?(i<3?1:1-ease(u*3)):0);
 const cond=i<3?0:i==3?ease(u/.8):1;chromatin.setAttribute('opacity',i<3?1:1-cond);
 // centrioles
 const cs=i<4?0:i==4?ease(u):1;const top=[CX,lerp(420,300,cs)],bot=[CX,lerp(420,900,cs)];
 if(i>=12){top[1]=lerp(300,272,ck);bot[1]=lerp(900,928,ck)}
 cent[0].setAttribute('transform',`translate(${top})`);cent[1].setAttribute('transform',`translate(${bot})`);cent.forEach(c=>c.setAttribute('opacity',i<3?0:i==3?ease(u):i>=11?1-ease(segU(11,t)/.6)*(i==11)-(i>11):1));
 polar[0].setAttribute('opacity',0);
 // chromosomes
 const line=i<6?0:i==6?ease(u/.85):1, sep=i<9?0:i==9?ease((u-.1)/.9):1;
 const fade=i<11?1:i==11?1-ease(u/.7):0;
 chroms.forEach((c,k)=>{const [sx,sy,sr]=start[k];const ex=216+k*96;const x=lerp(sx,ex,line),y=lerp(sy,CY,line),r=lerp(sr,0,line);
  const ax=lerp(x,CX+(ex-CX)*0.5,sep);
  c.g.setAttribute('transform',`translate(0,0)`);c.g.setAttribute('opacity',cond*fade);
  c.sis.forEach((s,j)=>{const off=(j?1:-1)*11;const yy=lerp(y,j?770:430,sep);const sc=lerp(0.5,1,cond);
   const ox=Math.sin(r)*off*-1,oy=Math.cos(r)*off;s.setAttribute('transform',`translate(${sep?ax:x+ox*(1-sep)},${sep?yy+off*0.0:y+oy}) rotate(${r*57.3}) scale(${sc})`)});
  set(c.cm,{cx:x,cy:y,opacity:sep>0.05?0:1});
  // fibres
  const fa=i<7?0:i==7?ease(u/.5):i<11?1:i==11?1-ease(u/.5):0;
  [0,1].forEach(j=>{const f=fibers[k*2+j];const p=j?bot:top;const yy=sep?lerp(y,j?770:430,sep)+(j?-10:10):y+(j?11:-11);const xx=sep?ax:x;set(f,{x1:p[0],y1:p[1],x2:xx,y2:yy,opacity:fa})})});
 const ka=i==7?ease((u-.2)/.3):0;set(kin,{x:248,y:CY-36,opacity:ka});
 plate.setAttribute('opacity',(i>=6&&i<=8)?1:0);plateT.setAttribute('opacity',(i>=6&&i<=8)?1:0);
 const dnA=i<11?0:i==11?ease((u-.2)/.8):1;dn.forEach(d=>{d.setAttribute('opacity',dnA);d.setAttribute('cy',d===dn[0]?lerp(430,430,0):770)});daughterChrom.forEach(d=>d.setAttribute('opacity',dnA));
 ST=STATE();
 if(i<=1){const k=ease((t-4.2)/2.2);placeMascot(masc,lerp(360,600,k),lerp(600,960-60,k)+(i==0?-Math.abs(Math.sin(t*4))*20:0),lerp(1.3,0.4,k),t,1-ease((t-6)/0.6))}
 else if(i>=13){placeMascot(masc,600,880-Math.abs(Math.sin(t*5))*24,0.45,t,ease((t-S(13))/0.4))}else masc.setAttribute('opacity',0);}
const num=s=>(s||'').match(/-?\d*\.?\d+(?:e-?\d+)?/g)?.map(Number)||[];
function STATE(){const o=e=>+(e.getAttribute('opacity')??1);
 return {cells:eS.map(e=>['cx','cy','rx','ry'].map(a=>+e.getAttribute(a))),nuc:o(nuc),chromatin:o(chromatin),dn:o(dn[0]),
 cent:cent.map(c=>[...num(c.getAttribute('transform')),o(c)]),
 chroms:chroms.map(c=>({op:o(c.g),sis:c.sis.map(s=>num(s.getAttribute('transform'))),cm:[+c.cm.getAttribute('cx'),+c.cm.getAttribute('cy'),o(c.cm)]})),
 fib:fibers.map(f=>['x1','y1','x2','y2'].map(a=>+f.getAttribute(a)).concat(o(f))),masc:masc.getAttribute('opacity')==='0'?[0,0,0,0,1]:masc._st}}
function seek2(t){seek0(t);ST.masc=masc.getAttribute('opacity')==='0'?[0,0,0,0,1]:masc._st}
const seek0=seek;window.seek=seek2;
