setSegments([
 {c:'Why does your heart go *lub-dub*?',d:3.6,hook:1},
 {c:'One heartbeat is one *cardiac cycle*.',d:3.0},
 {c:'At about 72 beats a minute, it lasts *0.8 seconds*.',d:3.6},
 {c:'First, the *atria contract*.',d:2.8},
 {c:'They push blood through the open *tricuspid* and *bicuspid* valves into the ventricles.',d:5.6},
 {c:'Next, the *ventricles contract*.',d:2.8},
 {c:'The AV valves slam shut. That’s the *LUB*.',d:4.0},
 {c:'The *semilunar valves* open.',d:2.8},
 {c:'Blood is pumped into the *pulmonary artery* and the *aorta*.',d:4.6},
 {c:'Finally, everything *relaxes*.',d:2.8},
 {c:'The semilunar valves close. That’s the *DUB*.',d:4.0},
 {c:'Blood flows into the atria again.',d:3.2},
 {c:'Remember the order: *atria → ventricles → relax*.',d:4.6},
 {c:'Follow for the next chapter.',d:2.6},
]);
header('BIOLOGY IN 50 SECONDS · CLASS 11','The Cardiac Cycle');
const RB='#cfdcf7',RS='#3f63b8',LB='#f7d0cd',LS='#b8403a';
const heart=dia(el('g',{}));
// arteries
const pa=el('path',{d:'M100,250 L140,250 L140,560 L160,560 L160,610 L100,610 Z',fill:RB,stroke:RS,'stroke-width':5,'stroke-linejoin':'round'},heart);
const ao=el('path',{d:'M620,250 L580,250 L580,560 L560,560 L560,610 L620,610 Z',fill:LB,stroke:LS,'stroke-width':5,'stroke-linejoin':'round'},heart);
txt('Pulmonary',{x:120,y:212,'text-anchor':'middle','font-size':20,'font-weight':600,fill:RS},heart);
txt('artery',{x:120,y:236,'text-anchor':'middle','font-size':20,'font-weight':600,fill:RS},heart);
txt('Aorta',{x:600,y:236,'text-anchor':'middle','font-size':20,'font-weight':600,fill:LS},heart);
txt('from body',{x:245,y:226,'text-anchor':'middle','font-size':19,fill:'#6b6258'},heart);
txt('from lungs',{x:475,y:226,'text-anchor':'middle','font-size':19,fill:'#6b6258'},heart);
const ch={};function chamber(k,x,y,w,h,f,s,l1){const g=el('g',{},heart);el('rect',{x,y,width:w,height:h,rx:34,fill:f,stroke:s,'stroke-width':6},g);
 txt(l1,{x:x+w/2,y:y+h/2+8,'text-anchor':'middle','font-size':22,'font-weight':600,fill:s,opacity:.8},g);ch[k]={g,cx:x+w/2,cy:y+h/2}}
chamber('RA',150,300,190,170,RB,RS,'Right atrium');chamber('LA',380,300,190,170,LB,LS,'Left atrium');
chamber('RV',150,500,190,270,RB,RS,'Right ventricle');chamber('LV',380,500,190,270,LB,LS,'Left ventricle');
function flap(color){return el('line',{stroke:color,'stroke-width':9,'stroke-linecap':'round'},heart)}
const av=[[178,1,RS],[312,-1,RS],[408,1,LS],[542,-1,LS]].map(([x,dir,c])=>({x,dir,l:flap(c)}));
const sl=[[100,1,RS],[140,-1,RS],[580,1,LS],[620,-1,LS]].map(([x,dir,c])=>({x,dir,l:flap(c)}));
txt('tricuspid',{x:245,y:492,'text-anchor':'middle','font-size':17,fill:RS,opacity:.0,id:'tl'},heart);
const dots=el('g',{},heart);const D=[];for(let i=0;i<48;i++)D.push(el('circle',{r:7},dots));
const masc=dia(makeMascot());finishOverlay();
const phaseNames=pills(['Atria contract','Ventricles contract','Relax'],850);phaseNames.forEach(p=>p.g.setAttribute('opacity',0));
const timer=el('g',{opacity:0});el('rect',{x:110,y:830,width:500,height:22,rx:11,fill:'#e9e1d4'},timer);const tf=el('rect',{x:110,y:830,width:0,height:22,rx:11,fill:'#e8803f'},timer);
txt('0 s',{x:110,y:885,'font-size':22,fill:'#6b6258'},timer);txt('0.8 s',{x:610,y:885,'text-anchor':'end','font-size':22,fill:'#6b6258'},timer);
const pop=txt('',{x:360,y:500,'text-anchor':'middle','font-size':84,'font-weight':800,fill:'#1f2430',stroke:'#f6f1e8','stroke-width':10,'paint-order':'stroke'});
const legend=el('g',{opacity:0});txt('Lub = AV valves close',{x:360,y:828,'text-anchor':'middle','font-size':28,'font-weight':700,fill:'#1f2430'},legend);
txt('Dub = semilunar valves close',{x:360,y:874,'text-anchor':'middle','font-size':28,'font-weight':700,fill:'#1f2430'},legend);
const MAP={3:[0,.35],4:[.35,1],5:[1,1.05],6:[1.05,1.15],7:[1.15,1.25],8:[1.25,1.9],9:[1.9,2],10:[2,2.15],11:[2.15,3]};
function phaseAt(t){const i=segAt(t);if(i<3)return 0;if(MAP[i])return lerp(MAP[i][0],MAP[i][1],segU(i,t));return((t-STARTS[12])/0.8*3)%3}
function sq(g,c,s){g.setAttribute('transform',`translate(${c.cx},${c.cy}) scale(${1-0.12*s},${1-0.1*s}) translate(${-c.cx},${-c.cy})`)}
function seek(t){caption(t);const i=segAt(t),p=phaseAt(t),loop=i>=12;
 const aS=p<1?Math.sin(Math.PI*p):0,vS=(p>=1&&p<2)?Math.sin(Math.PI*(p-1)):0;
 sq(ch.RA.g,ch.RA,aS);sq(ch.LA.g,ch.LA,aS);sq(ch.RV.g,ch.RV,vS);sq(ch.LV.g,ch.LV,vS);
 const avO=p<1.05?1:p<1.12?1-(p-1.05)/.07:p<2.15?0:p<2.3?(p-2.15)/.15:1;
 const slO=p<1.15?0:p<1.22?(p-1.15)/.07:p<2?1:p<2.1?1-(p-2)/.1:0;
 for(const f of av){const a=avO*1.25;set(f.l,{x1:f.x,y1:485,x2:f.x+f.dir*62*Math.cos(a),y2:485+62*Math.sin(a)})}
 for(const f of sl){const a=-slO*1.3;set(f.l,{x1:f.x,y1:540,x2:f.x+f.dir*20*Math.cos(a),y2:540+20*Math.sin(a)})}
 // blood dots
 const flows=[];const fAV=p<1?1:(p>2.3?0.5:0),fOut=slO>0.5&&p<2?1:0,fIn=p>1.1?0.7:0;
 const sp=loop?2.2:0.45;
 flows.push([[[245,360],[245,640]],RS,fAV],[[[475,360],[475,640]],LS,fAV]);
 flows.push([[[245,650],[200,585],[120,585],[120,260]],RS,fOut],[[[475,650],[520,585],[600,585],[600,260]],LS,fOut]);
 flows.push([[[245,240],[245,380]],RS,fIn],[[[475,240],[475,380]],LS,fIn]);
 D.forEach((d,k)=>{const fl=flows[k%6],j=Math.floor(k/6);if(!fl[2]){d.setAttribute('opacity',0);return}
  const f=((j/8)+t*sp*(fl[2]))%1;const [x,y]=poly(fl[0],f);set(d,{cx:x+((j*37)%11-5),cy:y,fill:fl[1],opacity:Math.min(1,Math.sin(Math.PI*f)*2)})});
 // mascot
 if(i==0){const u=segU(0,t),k=ease((u-.35)/.65);placeMascot(masc,lerp(360,245,k),lerp(860,400,k),lerp(1.5,0.3,k),t,1)}
 else if(i<12){let x=245,y=400,op=1;
  if(p>=.35&&p<1){y=lerp(400,640,ease((p-.35)/.65))}else if(p>=1&&p<1.25)y=640;
  else if(p>=1.25&&p<1.9){const [a,b]=poly([[245,640],[200,585],[120,585],[120,280]],ease((p-1.25)/.65));x=a;y=b;op=1-ease((p-1.7)/.2)}
  else if(p>=1.9&&p<2.15)op=0;else if(p>=2.15){y=lerp(230,400,ease((p-2.15)/.85));op=ease((p-2.15)/.2)}
  placeMascot(masc,x,y+Math.sin(t*6)*3,0.3,t,op)}
 else if(i==13){placeMascot(masc,360,470-Math.abs(Math.sin(t*5))*30,0.6,t,ease(segU(13,t)/0.2))}else masc.setAttribute('opacity',0);
 ST={sq:[aS,aS,vS,vS],avO,slO,dots:D.map(d=>[+d.getAttribute('cx')||0,+d.getAttribute('cy')||0,d.getAttribute('fill')==RS?0:1,+(d.getAttribute('opacity')||0)]),masc:masc._st&&masc.getAttribute('opacity')!=='0'?masc._st:[0,0,0,0,1]};
 // overlays
 timer.setAttribute('opacity',(i==1||i==2)?1:0);tf.setAttribute('width',i==2?500*ease(segU(2,t)/0.8):0);
 const showP=i>=3&&i<=12;phaseNames.forEach((q,k)=>{q.g.setAttribute('opacity',showP?1:0);q.on(Math.floor(p)==k&&i>=3)});
 legend.setAttribute('opacity',i==13?1:0);
 let w='',s=1;if(i==6){w='LUB';s=ease(segU(6,t)/.12)}else if(i==10){w='DUB';s=ease(segU(10,t)/.12)}
 else if(loop){if(p>=1.05&&p<1.5)w='lub';else if(p>=2&&p<2.45)w='dub'}
 pop.textContent=w;pop.setAttribute('font-size',loop?60:84);pop.setAttribute('opacity',w&&!(i==13&&false)?1:0);
 pop.setAttribute('transform',`translate(360,488) scale(${0.6+0.4*s}) translate(-360,-488)`)}
window.seek=seek;
