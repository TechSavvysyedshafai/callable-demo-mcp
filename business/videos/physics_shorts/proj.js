setSegments([
 {c:'Drop one ball, throw another sideways. Which lands first?',d:3.4,hook:1},
 {c:'*Projectile motion*: two motions happening at once.',d:3.4,hook:1},
 {c:'*Horizontal*: no force, so the speed stays constant.',d:3.2},
 {c:'*Vertical*: gravity pulls down, *g = 9.8 m/s²*.',d:3.2},
 {c:'Split the launch speed u: *v<sub>x</sub> = u cos θ*, *v<sub>y</sub> = u sin θ*.',d:3.6},
 {c:'Going up, v<sub>y</sub> shrinks. At the top, *v<sub>y</sub> = 0*.',d:3.4},
 {c:'Coming down, it grows again. The path is *symmetric*.',d:3.4},
 {c:'Time of flight: *T = 2u sin θ / g*.',d:3.4},
 {c:'Maximum height: *H = u² sin²θ / 2g*.',d:3.2},
 {c:'Range: *R = u² sin 2θ / g*.',d:3.2},
 {c:'Range is *largest at 45°*.',d:3.4},
 {c:'*30° and 60°* give the *same range*.',d:3.0},
 {c:'x grows with t, y with t². That makes a *parabola*.',d:3.4},
 {c:'Back to the start: both balls hit the ground *together*.',d:3.6},
 {c:'Remember: *split it*, horizontal and vertical.',d:2.8},
]);
header('PHYSICS IN 50 SECONDS · CLASS 11','Projectile Motion');
// ---- physics (design px). 1 m = SC px. g = 9.8 m/s². Slow motion: real time = playback time × RATE.
const SC=50,G=9.8,U=10,LX=100,GY=820,RATE=0.5,ASC=14;   // ASC: arrow px per m/s
const PH=5*SC, PX=190, PLAT=[60,GY-PH,100,PH];           // hook platform: 5 m high, balls start at x=PX
const CB=['#e8803f','#d62828','#3b82c4','#2e9e6b','#8e5aa8','#2b2b2b'];   // orange red blue green purple dark
const rad=d=>d*Math.PI/180;
const traj=(u,th,t)=>[LX+u*Math.cos(rad(th))*t*SC, GY-(u*Math.sin(rad(th))*t-0.5*G*t*t)*SC];
const TOF=(u,th)=>2*u*Math.sin(rad(th))/G;
const T45=TOF(U,45), TF=Math.sqrt(2*5/G);               // 1.443 s, 1.010 s
const world=dia(el('g',{}));
el('rect',{x:-400,y:GY,width:1520,height:30,fill:'#9ccc83'},world); el('rect',{x:-400,y:GY+30,width:1520,height:400,fill:'#c9a27a'},world);
const platE=el('rect',{x:PLAT[0],y:PLAT[1],width:PLAT[2],height:PLAT[3],fill:'#9aa7b5',stroke:'#6b7a8a','stroke-width':4},world);
const baseE=el('rect',{x:LX-30,y:GY-22,width:60,height:22,rx:5,fill:'#4a5a6a'},world);
const barrel=el('rect',{x:-8,y:-64,width:16,height:70,rx:5,fill:'#6b7a8a'},world);
const dotG=el('g',{},world); const dots=[0,1,2].map(ci=>[...Array(20)].map(()=>el('circle',{r:5,opacity:0.55},dotG)));
const balls=[0,1,2,3,4].map(k=>el('circle',{r:14,stroke:'#fff','stroke-width':3},world));
const masc=makeMascot(world);
const bands=[el('rect',{x:0,y:0,width:720,height:172,fill:'#f6f1e8'}),el('rect',{x:0,y:940,width:720,height:340,fill:'#f6f1e8'})];
for(const e of [...svg.querySelectorAll(':scope > text')].slice(0,2))svg.appendChild(e);svg.appendChild(_bar);
// ---- screen-space overlay
const lab=(s,attrs)=>txt(s,Object.assign({'font-size':24,'font-weight':600,fill:'#2b2b2b','text-anchor':'middle'},attrs));
function fml(parts,attrs){const e=txt('',Object.assign({'font-size':30,'font-weight':700,fill:'#1f2430','text-anchor':'middle'},attrs));e.textContent='';
 for(const p of parts){const s=document.createElementNS(NS,'tspan');if(typeof p=='string')s.textContent=p;else{s.textContent=p.sub;s.setAttribute('baseline-shift','sub');s.setAttribute('font-size','70%')}e.appendChild(s)}return e}
const card=el('rect',{x:70,y:196,width:580,height:66,rx:16,fill:'#fff',stroke:'#e9e1d4','stroke-width':3});
const f1=fml(['T = 2u sin θ / g']),f2=fml(['H = u² sin²θ / 2g']),f3=fml(['R = u² sin 2θ / g']);
const f4=fml(['x = v',{sub:'x'},' t']),f5=fml(['y = v',{sub:'y'},' t − ½ g t²']);
const uT=lab('u',{fill:'#2b2b2b','font-size':28}),vxT=fml(['v',{sub:'x'},' = u cos θ'],{'font-size':26,fill:'#3b82c4'}),vyT=fml(['v',{sub:'y'},' = u sin θ'],{'font-size':26,fill:'#d62828'});
const thT=lab('θ',{'font-size':26}),vx2=fml(['v',{sub:'x'}],{'font-size':24,fill:'#3b82c4'}),vy2=fml(['v',{sub:'y'}],{'font-size':24,fill:'#d62828'});
const gT=lab('g = 9.8 m/s²',{fill:'#d62828'}),topT=fml(['v',{sub:'y'},' = 0'],{'font-size':26,fill:'#d62828'});
const tT=lab('t = 0.0 s',{fill:'#2b2b2b'}),HT=lab('H',{fill:'#2e9e6b','font-size':28}),RT=lab('R',{fill:'#8e5aa8','font-size':28});
const a30=lab('30°',{fill:CB[3]}),a45=lab('45°',{fill:CB[0]}),a60=lab('60°',{fill:CB[4]}),sameT=lab('same range',{fill:'#8e5aa8'}),parT=lab('parabola',{fill:'#e8803f'});
const sameHT=lab('same height, every moment',{fill:'#6b7a8a'}),constT=lab('constant',{fill:'#3b82c4'}),growT=lab('growing',{fill:'#d62828'});
const uA=arrow(svg,'#2b2b2b'),vxA=arrow(svg,'#3b82c4'),vyA=arrow(svg,'#d62828'),gA=arrow(svg,'#d62828');
const thArc=el('path',{fill:'none',stroke:'#2b2b2b','stroke-width':3});
const dimL=el('g',{stroke:'#2e9e6b','stroke-width':4,'stroke-linecap':'round','stroke-dasharray':'10 8'});const dim1=el('line',{},dimL),dim2=el('line',{},dimL),dim3=el('line',{},dimL);
const vlines=[...Array(8)].map(()=>el('line',{stroke:'#3b82c4','stroke-width':3,'stroke-dasharray':'8 8'}));
const link=el('line',{stroke:'#6b7a8a','stroke-width':4,'stroke-dasharray':'10 8'});
const ring=el('circle',{r:26,fill:'none',stroke:'#8e5aa8','stroke-width':5});
const pA1=pills(['Horizontal','Vertical'],925), pA2=pills(['Split','Horizontal','Vertical'],925);
finishOverlay();
const r1=v=>Math.round(v*10)/10;
let VW={z:1,cx:360,cy:560};const V=(x,y)=>[360+(x-VW.cx)*VW.z,555+(y-VW.cy)*VW.z];
function place(e,x,y,op,extra){const [sx,sy]=V(x,y);set(e,Object.assign({x:r1(sx),y:r1(sy+8),opacity:op},extra||{}))}
const ARC=[1.2,355,720], WIDE=[1,360,560], ZOOM=[2.2,200,740];
const camL=(a,b,e)=>[lerp(a[0],b[0],e),lerp(a[1],b[1],e),lerp(a[2],b[2],e)];
const S=k=>STARTS[k];
function seek(t){caption(t);const i=segAt(t),u=segU(i,t),st=t-S(i);
 // ---- motion
 let bl=[],dt=[[],[],[]],plat=0,barTh=45,barOp=1,cam;
 const dotsFor=(ci,u0,th,tr)=>{for(let k=0;k*0.1<=tr;k++){dt[ci].push([...traj(u0,th,k*0.1),ci])}}
 const hookT=Math.max(0,st-0.4)*RATE, hr=Math.min(hookT,TF);
 const hook=()=>{plat=1;barOp=0;const fy=PLAT[1]-14+(0.5*G*hr*hr)*SC;bl.push([PX-12,fy,1]);bl.push([PX+18+4*hr*SC,fy,2])};
 let tr=0;   // real flight time of the main 45° ball
 if(i==0||i==13)hook();
 else if(i==1||i==2||i==3||i==7){tr=Math.min(Math.max(0,st-0.15)*RATE,T45);bl.push([...traj(U,45,tr),0]);dotsFor(0,U,45,tr)}
 else if(i==4){bl.push([LX,GY-14,0])}
 else if(i==5){tr=Math.min(st*RATE,T45/2);bl.push([...traj(U,45,tr),0]);dotsFor(0,U,45,tr)}
 else if(i==6){tr=Math.min(T45/2+st*RATE,T45);bl.push([...traj(U,45,tr),0]);dotsFor(0,U,45,tr)}
 else if(i==8){bl.push([...traj(U,45,T45/2),0]);dotsFor(0,U,45,T45)}
 else if(i==9||i==12){bl.push([...traj(U,45,T45),0]);dotsFor(0,U,45,T45)}
 else if(i==10||i==11){const t3=i==10?Math.max(0,st-0.2)*0.6:9;[[30,3,1],[45,0,0],[60,4,2]].forEach(([th,ci,di])=>{const tt=Math.min(t3,TOF(U,th));bl.push([...traj(U,th,tt),ci]);dotsFor(di,U,th,tt)});barTh=45}
 else if(i==14){bl.push([...traj(U,45,T45),0]);dotsFor(0,U,45,T45)}
 const b0=bl[0];const vx=U*Math.cos(rad(45)),vy=U*Math.sin(rad(45))-G*tr;
 // ---- camera
 if(i==0)cam=WIDE; else if(i==1)cam=camL(WIDE,ARC,ease(u/.4)); else if(i<=3)cam=ARC;
 else if(i==4)cam=camL(ARC,ZOOM,ease(u/.4));
 else if(i==5){const e=ease(u/.4);cam=camL(ZOOM,[1.6,b0[0],b0[1]+30],e)}
 else if(i==6){const f=[1.6,Math.min(b0[0],470),b0[1]+30];cam=camL(f,ARC,ease((u-.45)/.45))}
 else if(i<=12)cam=ARC; else if(i==13)cam=camL(ARC,WIDE,ease(u/.3)); else cam=WIDE;
 VW={z:cam[0],cx:cam[1],cy:cam[2]};world.setAttribute('transform',`translate(360,555) scale(${VW.z}) translate(${-VW.cx},${-VW.cy})`);
 // ---- 2D draw
 platE.setAttribute('opacity',plat);baseE.setAttribute('opacity',barOp);barrel.setAttribute('opacity',barOp);barrel.setAttribute('transform',`translate(${LX},${GY-14}) rotate(${90-barTh})`);
 balls.forEach((e,k)=>{const b=bl[k];if(!b){e.setAttribute('opacity',0);return}set(e,{cx:r1(b[0]),cy:r1(b[1]),fill:CB[b[2]],opacity:1})});
 dots.forEach((arr,ci)=>arr.forEach((e,k)=>{const d=dt[ci][k];if(!d){e.setAttribute('opacity',0);return}set(e,{cx:r1(d[0]),cy:r1(d[1]),fill:CB[d[2]],opacity:0.55})}));
 // mascot
 let mop=0;if(i==0||i==13)mop=1;else if(i==14)mop=ease(u/.3);
 if(mop>0){const w=i==14?Math.PI*2.2:0;const p=((t*w)%Math.PI)/Math.PI;const h=w?Math.sin(p*Math.PI)*28:0;const sq=w?1-0.22*Math.cos(2*Math.PI*p):1;
  placeMascot(masc,i==14?560:600,GY-28-h,0.6,t,mop,sq)}else masc.setAttribute('opacity',0);
 // ---- overlay
 const k=0.85, hide=e=>e.setAttribute('opacity',0);
 [uA,vxA,vyA,gA].forEach(a=>a.at(0,0,0,0,0));[card,f1,f2,f3,f4,f5,uT,vxT,vyT,thT,vx2,vy2,gT,topT,tT,HT,RT,a30,a45,a60,sameT,parT,sameHT,constT,growT,thArc,dim1,dim2,dim3,link,ring,...vlines].forEach(hide);
 const [bx,by]=V(b0[0],b0[1]);
 if(i==2||i==5||i==6){const op=i==2?ease((u-.1)/.3):1;vxA.at(bx,by,bx+vx*ASC*VW.z,by,op);if(i==2)place(constT,b0[0],b0[1]-34,op,{'text-anchor':'start'});
  if(i==2)vlines.forEach((l,k)=>{const d=dt[0][k*2];if(!d)return;const [x]=V(d[0],0),[,y1]=V(0,d[1]),[,y2]=V(0,GY);set(l,{x1:r1(x),x2:r1(x),y1:r1(y1),y2:r1(y2),opacity:0.8})})}
 if(i==3||i==5||i==6){const op=i==3?ease((u-.1)/.3):1;vyA.at(bx,by,bx,by-vy*ASC*VW.z,Math.abs(vy)<0.4?0:op);if(i==3)place(growT,b0[0]+24,b0[1]+(vy<0?-20:50),op,{'text-anchor':'start'})}
 if(i==3){const [ax,ay]=V(560,470),[bx2,by2]=V(560,545);gA.at(ax,ay,bx2,by2,ease(u/.3));place(gT,560,590,ease(u/.3))}
 if(i==4){const e1=ease((u-.35)/.25),e2=ease((u-.6)/.3),L=U*ASC*VW.z;const c=Math.cos(rad(45)),s=Math.sin(rad(45));
  uA.at(bx,by,bx+L*c,by-L*s,e1);place(uT,b0[0]+52,b0[1]-62,e1);
  vxA.at(bx,by,bx+L*c,by,e2);vyA.at(bx+L*c,by,bx+L*c,by-L*s,e2);
  place(vxT,b0[0]+150,b0[1]+40,e2,{'text-anchor':'start'});place(vyT,b0[0]+112,b0[1]-120,e2,{'text-anchor':'start'});
  const r=40;set(thArc,{d:`M${bx+r},${by} A${r},${r} 0 0 0 ${bx+r*c},${by-r*s}`,opacity:e1});place(thT,b0[0]+26,b0[1]-14,e1)}
 if(i==5&&u>.45)place(topT,b0[0],b0[1]-48,ease((u-.45)/.25));
 if(i==7){place(tT,b0[0],b0[1]-40,1);tT.textContent=tr>=T45?'T = 1.4 s':'t = '+tr.toFixed(1)+' s';card.setAttribute('opacity',1);f1.setAttribute('opacity',1);place(f1,0,0,1);set(f1,{x:360,y:240})}
 const showCard=(f)=>{card.setAttribute('opacity',1);set(f,{x:360,y:240,opacity:1})};
 if(i==8){showCard(f2);const [ax,ay]=V(b0[0],b0[1]),[,gy]=V(0,GY);set(dim1,{x1:r1(ax),y1:r1(ay+18),x2:r1(ax),y2:r1(gy),opacity:1});place(HT,b0[0]+30,(b0[1]+GY)/2,1)}
 if(i==9){showCard(f3);const [x1,gy]=V(LX,GY+40),[x2]=V(b0[0],0);set(dim2,{x1:r1(x1),y1:r1(gy),x2:r1(x2),y2:r1(gy),opacity:1,stroke:'#8e5aa8'});place(RT,(LX+b0[0])/2,GY+80,1)}
 if(i==10||i==11){const ends=[[30,a30,3],[45,a45,0],[60,a60,4]];ends.forEach(([th,e,ci])=>{const p=traj(U,th,TOF(U,th)/2);place(e,p[0],p[1]-30,i==10?ease((u-.6)/.3):1)});
  if(i==11){const p=traj(U,30,TOF(U,30));const [rx,ry]=V(p[0],p[1]);set(ring,{cx:r1(rx),cy:r1(ry),opacity:ease(u/.3)});place(sameT,p[0],p[1]-48,ease(u/.3))}}
 if(i==12){card.setAttribute('height',106);set(card,{opacity:1});set(f4,{x:360,y:232,opacity:1});set(f5,{x:360,y:282,opacity:1});const p=traj(U,45,T45*0.3);place(parT,p[0]-10,p[1]-30,ease((u-.3)/.3))}else card.setAttribute('height',66);
 if(i==13){const [x1,y1]=V(bl[0][0],bl[0][1]),[x2]=V(bl[1][0],0);set(link,{x1:r1(x1),y1:r1(y1),x2:r1(x2),y2:r1(y1),opacity:1});place(sameHT,340,PLAT[1]-70,ease((u-.2)/.3))}
 if(i==14){const [x0,y0]=V(355,700);vxA.at(x0-110,y0,x0-10,y0,1);vyA.at(x0+60,y0-60,x0+60,y0+40,1);place(vx2,300,650,1);place(vy2,455,742,1)}
 pA1.forEach((p,k)=>{p.g.setAttribute('opacity',i>=1&&i<=13?1:0);p.on(k==0?(i>=2):(i>=3))});
 pA2.forEach((p,k)=>{p.g.setAttribute('opacity',i==14?1:0);p.on(i==14&&u*3.6>k+0.5)});
 ST={view:[r1(VW.z*100)/100,r1(VW.cx),r1(VW.cy)],plat,bar:[LX,GY-14,barTh,barOp],balls:bl.map(b=>[r1(b[0]),r1(b[1]),b[2]]),dots:dt.flat().map(d=>[r1(d[0]),r1(d[1]),d[2]]),
  masc:masc.getAttribute('opacity')==='0'?[0,0,0,0,1,1]:masc._st};}
