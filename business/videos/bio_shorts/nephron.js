setSegments([
 {c:'You make about *180 litres* of filtrate a day…',d:4.4,hook:1},
 {c:'…but only *1 to 1.5 litres* of urine.',d:3.6,hook:1},
 {c:'Where does the rest go?',d:2.6,hook:1},
 {c:'Urine forms in *three steps*.',d:2.8},
 {c:'Step 1: *Filtration*.',d:2.3},
 {c:'Blood pressure in the *glomerulus* pushes water and small molecules into *Bowman’s capsule*.',d:6.0},
 {c:'Step 2: *Reabsorption*.',d:2.3},
 {c:'The *PCT* takes back nearly all the glucose and amino acids, and most of the water and salts.',d:6.2},
 {c:'The *loop of Henle* helps make the urine concentrated.',d:4.2},
 {c:'Step 3: *Secretion*.',d:2.3},
 {c:'The *DCT* adds extra H⁺, K⁺ and ammonia to the filtrate.',d:4.6},
 {c:'The *collecting duct* takes back more water, so the urine becomes concentrated.',d:5.2},
 {c:'*Filtration → reabsorption → secretion.* That’s the order.',d:4.6},
]);
header('BIOLOGY IN 50 SECONDS · CLASS 11','How Urine Forms');
const steps=pills(['1 Filtration','2 Reabsorption','3 Secretion'],190);
const T='M228,384 C262,432 334,382 322,442 C310,502 402,472 382,532 C362,592 300,562 330,612 L330,850 C330,905 420,905 420,850 L420,562 C420,502 522,522 502,462 C482,402 562,382 584,432 C604,472 620,470 620,505 L620,905';
const g=el('g',{});
el('path',{d:'M40,300 C100,300 120,318 165,322',fill:'none',stroke:'#c0392b','stroke-width':16,'stroke-linecap':'round'},g);
el('path',{d:'M165,345 C120,352 100,372 40,372',fill:'none',stroke:'#c0392b','stroke-width':12,'stroke-linecap':'round',opacity:.8},g);
el('path',{d:T,fill:'none',stroke:'#9a7b3c','stroke-width':34,'stroke-linecap':'round','stroke-linejoin':'round'},g);
const tube=el('path',{d:T,fill:'none',stroke:'#f6e3ad','stroke-width':24,'stroke-linecap':'round','stroke-linejoin':'round'},g);
el('path',{d:'M155,276 A64,64 0 1,1 155,384',fill:'#eef3fb',stroke:'#9a7b3c','stroke-width':10},g);
for(const [x,y] of[[185,312],[205,334],[180,348],[200,312],[214,318],[188,330]])el('circle',{cx:x,cy:y,r:15,fill:'#e06b5e',stroke:'#c0392b','stroke-width':3},g);
const L=(s,x,y,a='middle',sz=21,c='#5a4a2a')=>txt(s,{x,y,'text-anchor':a,'font-size':sz,'font-weight':600,fill:c},g);
L('← Glomerulus',262,340,'start',20);L('Bowman’s capsule',200,430,'middle',19);L('PCT',300,500,'end');L('Loop of Henle',375,945);
L('DCT',540,500);const cdl=L('Collecting duct',0,0);cdl.setAttribute('transform','translate(668,720) rotate(-90)');
L('blood in',40,288,'start',17,'#c0392b');L('blood out',40,398,'start',17,'#c0392b');
const len=tube.getTotalLength();function near(x,y){let b=0,bd=1e9;for(let k=0;k<=600;k++){const q=tube.getPointAtLength(len*k/600);const d=Math.hypot(q.x-x,q.y-y);if(d<bd){bd=d;b=k/600}}return b}
const fP=near(330,612),fL=near(420,562),fD=near(620,505);
// arrows
const reab=[],sec=[],wat=[],loopw=[];
for(let k=0;k<4;k++)reab.push(arrow(g,'#2f9e6b'));for(let k=0;k<3;k++)sec.push(arrow(g,'#8a4fc4'));for(let k=0;k<4;k++)wat.push(arrow(g,'#3f7fd0'));for(let k=0;k<3;k++)loopw.push(arrow(g,'#3f7fd0'));for(let k=0;k<3;k++)loopw.push(arrow(g,'#2f9e6b'));
const filt=[];for(let k=0;k<8;k++)filt.push(el('circle',{r:5,fill:'#3f7fd0'},g));
const reabT=el('g',{});['Taken back:','glucose, amino acids,','most water & salts'].forEach((s,k)=>txt(s,{x:40,y:560+k*28,'font-size':21,'font-weight':k?500:700,fill:'#2f9e6b'},reabT));
const loopT=el('g',{});txt('water out',{x:270,y:740,'text-anchor':'end','font-size':21,'font-weight':700,fill:'#3f7fd0'},loopT);txt('salts out',{x:478,y:740,'font-size':21,'font-weight':700,fill:'#2f9e6b'},loopT);
const secT=txt('+ H⁺  K⁺  NH₃',{x:600,y:372,'text-anchor':'middle','font-size':26,'font-weight':700,fill:'#8a4fc4'});
const watT=el('g',{});['water','out'].forEach((s,k)=>txt(s,{x:690,y:548+k*24,'text-anchor':'middle','font-size':19,'font-weight':600,fill:'#3f7fd0'},watT));
const drop=el('circle',{fill:'#4a90d9',stroke:'#2c6aa8','stroke-width':3});const masc=makeMascot();
const cnt=el('g',{});const cv=txt('180 L',{x:520,y:290,'text-anchor':'middle','font-size':56,'font-weight':800,fill:'#1f2430'},cnt);
const cl=txt('filtrate per day',{x:520,y:322,'text-anchor':'middle','font-size':19,fill:'#6b6258'},cnt);
const urine=txt('Urine ≈ 1.5 L / day',{x:520,y:960-30,'text-anchor':'middle','font-size':24,'font-weight':700,fill:'#9a7b3c'});
function vol(t){const i=segAt(t);if(i<7)return 180;if(i==7)return lerp(180,45,ease(segU(7,t)));if(i==8)return lerp(45,25,ease(segU(8,t)));if(i<11)return 25;if(i==11)return lerp(25,1.5,ease(segU(11,t)));return 1.5}
function pos(t){const i=segAt(t),u=segU(i,t);
 if(i<4)return{q:null,x:lerp(40,170,ease((t-0)/8)),y:lerp(300,322,ease(t/8))};
 if(i==4)return{q:null,x:180,y:328};
 if(i==5){const k=ease((u-.45)/.55);return{q:null,x:lerp(180,232,k),y:lerp(328,392,k)}}
 const tab={6:[0,0.02],7:[0.02,fP],8:[fP,fL],9:[fL,fL+.03],10:[fL+.03,fD],11:[fD,0.985],12:[0.985,0.985]};
 const [a,b]=tab[i];const q=lerp(a,b,ease(u));const pt=tube.getPointAtLength(len*q);return{q,x:pt.x,y:pt.y}}
function norm(q){const a=tube.getPointAtLength(len*Math.max(0,q-.004)),b=tube.getPointAtLength(len*Math.min(1,q+.004));const dx=b.x-a.x,dy=b.y-a.y,m=Math.hypot(dx,dy)||1;return[-dy/m,dx/m]}
function seek(t){caption(t);const i=segAt(t),u=segU(i,t);
 steps.forEach((s,k)=>s.on(i==12?Math.floor(u*3.3)>=k:(k==0&&(i==4||i==5))||(k==1&&(i>=6&&i<=8))||(k==2&&(i==9||i==10))||(k==1&&i==11)));
 const v=vol(t);cv.textContent=(v<10?v.toFixed(1):Math.round(v))+' L';cl.textContent=i>=11&&v<3?'left as urine per day':'filtrate per day (approx.)';
 const P=pos(t),r=8+16*Math.sqrt(v/180);set(drop,{cx:P.x,cy:P.y,r});placeMascot(masc,P.x,P.y-r-12,0.26,t);
 const fa=i==5?Math.sin(Math.PI*u):0;filt.forEach((c,k)=>{const f=(k/8+t*0.8)%1;const a=k*0.8;set(c,{cx:195+Math.cos(a)*(15+f*30),cy:330+Math.sin(a)*(15+f*30),opacity:fa*(1-f)})});
 const ra=i==7?ease(u/.2):0;reab.forEach((A,k)=>{const q=0.02+(fP-0.02)*(k+.5)/4,pt=tube.getPointAtLength(len*q),[nx,ny]=norm(q);const s=k%2?1:-1;A.at(pt.x+nx*s*22,pt.y+ny*s*22,pt.x+nx*s*58,pt.y+ny*s*58,ra)});
 reabT.setAttribute('opacity',ra);
 const la=i==8?ease(u/.2):0;loopw.forEach((A,k)=>{const y=640+(k%3)*80;k<3?A.at(312,y,278,y,la):A.at(438,y,472,y,la)});loopT.setAttribute('opacity',la);
 const sa=i==10?ease(u/.2):0;sec.forEach((A,k)=>{const q=fL+.03+(fD-fL-.03)*(k+.5)/3,pt=tube.getPointAtLength(len*q);A.at(pt.x+10,pt.y-62,pt.x+4,pt.y-22,sa)});secT.setAttribute('opacity',sa);
 const wa=i==11?ease(u/.2):0;wat.forEach((A,k)=>{const y=600+k*80;A.at(638,y,672,y,wa)});watT.setAttribute('opacity',wa);
 urine.setAttribute('opacity',0);}
window.seek=seek;
