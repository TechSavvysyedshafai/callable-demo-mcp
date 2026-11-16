setSegments([
 {c:'How does DNA make a *protein*?',d:3.2,hook:1},
 {c:'Two steps: *transcription*, then *translation*.',d:3.0,hook:1},
 {c:'*Step 1: Transcription*, inside the nucleus.',d:2.6},
 {c:'*RNA polymerase* opens the DNA at the *promoter*.',d:3.2},
 {c:'It reads the *template strand* and builds *mRNA*, 5′ → 3′.',d:3.6},
 {c:'In RNA, *U replaces T*: A pairs with U.',d:3.0},
 {c:'The mRNA is processed, then leaves the nucleus through a *nuclear pore*.',d:3.8},
 {c:'*Step 2: Translation*, at the *ribosome*.',d:3.0},
 {c:'The ribosome reads the mRNA *three bases at a time*: each triplet is a *codon*.',d:3.6},
 {c:'It starts at *AUG*, the start codon, which codes for *methionine*.',d:3.4},
 {c:'*tRNA* carries each amino acid. Its *anticodon* matches the codon.',d:3.8},
 {c:'Amino acids join by *peptide bonds*. The chain grows.',d:3.4},
 {c:'At a *stop codon* (UAA, UAG or UGA), the chain is released.',d:3.6},
 {c:'Result: a *protein*.',d:2.4},
 {c:'Remember the *central dogma*: DNA → RNA → Protein.',d:3.8},
]);
header('BIOLOGY IN 50 SECONDS · CLASS 12','Transcription & Translation');
// ---- constants (design px). The camera view maps design (cx,cy) at zoom z to screen (360,555).
const HY=420,HX0=160,HX1=560,R=20,PER=110,RS=22;
const BC=['#e0663a','#3b82c4','#2e9e6b','#e6b422','#d62828'];   // A U G C stop
const AC=['#8e5aa8','#e8803f','#2e9e6b','#3b82c4','#e6b422','#d2547a','#5b8c5a'];
const SEQ='AUGGCUUCAGACCGUUUGAACUAA', NB=24, CI=s=>'AUGC'.indexOf(s);
const seqD=i=>(((Math.imul(i,0x9E3779B1)>>>0)>>>13)%4), comp=c=>c^1;
const OLD='#3b4a5c',RNA='#2a9d5c';
const world=dia(el('g',{}));
const cell=el('ellipse',{cx:360,cy:560,rx:300,ry:360,fill:'#fbe3cc',stroke:'#c98b5a','stroke-width':8},world);
const nuc=el('circle',{cx:360,cy:420,r:150,fill:'#efc6a2',stroke:'#a8714a','stroke-width':5},world);
const pore=el('circle',{cx:360,cy:570,r:26,fill:'none',stroke:'#e6b422','stroke-width':8},world);
const rungG=el('g',{'stroke-width':6,'stroke-linecap':'round'},world);
const bb=(c,w)=>el('path',{fill:'none',stroke:c,'stroke-width':w,'stroke-linecap':'round','stroke-linejoin':'round'},world);
const pB=bb(OLD,8),pA=bb(OLD,8);
const polyE=el('ellipse',{rx:38,ry:30,fill:'#8e5aa8',stroke:'#fff','stroke-width':4},world);
const riboL=el('ellipse',{rx:95,ry:55,fill:'#9aa7b5',stroke:'#6b7a8a','stroke-width':4},world);
const mrna=bb(RNA,7); const mbG=el('g',{'stroke-width':5,'stroke-linecap':'round'},world);
const capE=el('circle',{r:11,fill:'#e6b422',stroke:'#fff','stroke-width':3},world);
const tailE=[0,1,2].map(()=>el('circle',{r:6,fill:'#e0663a'},world));
const riboS=el('ellipse',{rx:80,ry:38,fill:'#8795a4',stroke:'#6b7a8a','stroke-width':4},world);
const trnas=[0,1,2].map(()=>{const g=el('g',{},world);el('rect',{x:-7,y:-26,width:14,height:52,rx:6,fill:'#5b8c5a'},g);for(const dx of[-10,0,10])el('rect',{x:dx-3,y:26,width:6,height:10,rx:2,fill:'#3f6b3e'},g);const b=el('circle',{cy:-36,r:11,stroke:'#fff','stroke-width':3},g);g._b=b;return g});
const beads=[...Array(7)].map((_,j)=>el('circle',{r:12,fill:AC[j],stroke:'#fff','stroke-width':3},world));
const masc=makeMascot(world);
// mask bands so the zoomed cell never covers the title or caption zones (kept in overlay mode too)
const bands=[el('rect',{x:0,y:0,width:720,height:172,fill:'#f6f1e8'}),el('rect',{x:0,y:940,width:720,height:340,fill:'#f6f1e8'})];
for(const e of [...svg.querySelectorAll(':scope > text')].slice(0,2))svg.appendChild(e);svg.appendChild(_bar);
// ---- screen-space overlay (labels, pills, legend, codon marks)
const lab=(s,attrs)=>txt(s,Object.assign({'font-size':21,'font-weight':600,fill:'#2b2b2b','text-anchor':'middle'},attrs));
const nucT=lab('nucleus',{}),promT=lab('promoter',{}),polT=lab('RNA polymerase',{fill:'#6b3d85'}),tmplT=lab('template strand',{}),mT=lab('mRNA',{fill:'#1f6b45'});
const capT=lab('cap',{fill:'#8a6a10'}),tailT=lab('poly-A tail',{fill:'#8a6a10','text-anchor':'end'}),poreT=lab('nuclear pore',{fill:'#8a6a10'}),riboT=lab('ribosome',{fill:'#4a5a6a'});
const startT=lab('start codon',{fill:'#1f6b45'}),trT=lab('tRNA',{fill:'#3f6b3e'}),antiT=lab('anticodon',{fill:'#3f6b3e'}),pepT=lab('peptide bond',{}),stopT=lab('stop codon',{fill:'#d62828'}),protT=lab('protein',{fill:'#6b3d85'});
const trA=arrow(svg,'#3f6b3e'),antiA=arrow(svg,'#3f6b3e');
const letters=[...Array(NB)].map((_,i)=>txt(SEQ[i],{'text-anchor':'middle','font-weight':800,fill:BC[CI(SEQ[i])]}));
const codonL=[...Array(8)].map(()=>el('line',{stroke:'#8a7f72','stroke-width':4,'stroke-linecap':'round'}));
const legend=el('g',{});[['A',0,'U',1,850],['G',2,'C',3,892]].forEach(([a,ca,b,cb,y])=>{txt(a,{x:560,y:y+8,'text-anchor':'middle','font-size':24,'font-weight':800,fill:BC[ca]},legend);el('line',{x1:580,x2:612,y1:y,y2:y,stroke:'#b9a58c','stroke-width':4},legend);el('circle',{cx:596,cy:y,r:7,fill:BC[ca]},legend);txt(b,{x:632,y:y+8,'text-anchor':'middle','font-size':24,'font-weight':800,fill:BC[cb]},legend)});
const pA1=pills(['Transcription','Translation'],925), pA2=pills(['DNA','RNA','Protein'],925);
finishOverlay();
// ---- camera keyframes per segment start (z,cx,cy)
const K=[[1,360,560],[1.06,360,560],[1.06,360,560],[1.7,360,430],[1.7,360,430],[1.7,360,430],[1.7,360,430],[1.5,360,765],[1.8,360,735],[1.8,360,735],[1.8,360,735],[1.8,360,735],[1.8,360,735],[1.8,360,735],[1,360,560],[1,360,560]];
const r1=v=>Math.round(v*10)/10;
const dstr=pts=>pts.length>1?'M'+pts.map(p=>r1(p[0])+','+r1(p[1])).join('L'):'';
let VW={z:1,cx:360,cy:560};const V=(x,y)=>[360+(x-VW.cx)*VW.z,555+(y-VW.cy)*VW.z];
function place(e,x,y,op,extra){const [sx,sy]=V(x,y);set(e,Object.assign({x:r1(sx),y:r1(sy+8),opacity:op},extra||{}))}
const S=k=>STARTS[k];
function seek(t){caption(t);const i=segAt(t),u=segU(i,t);
 // camera
 const kv=i==6?ease((u-.3)/.7):ease(u);VW={z:lerp(K[i][0],K[i+1][0],kv),cx:lerp(K[i][1],K[i+1][1],kv),cy:lerp(K[i][2],K[i+1][2],kv)};
 world.setAttribute('transform',`translate(360,555) scale(${VW.z}) translate(${-VW.cx},${-VW.cy})`);
 const nucGlow=i<=1?0.5+0.5*Math.sin(t*4):0;nuc.setAttribute('stroke',i<=1?'#e8a43f':'#a8714a');
 // transcription
 const phi=0.4*t;
 const bx=i<3?250:i==3?250:i==4?lerp(250,360,u):i==5?lerp(360,470,u):470;
 const by=i==3?lerp(HY-130,HY,ease(u/.5)):HY;
 const pop=i<3?0:i==3?ease(u/.4):i<6?1:i==6?1-ease(u/.3):0;
 const ob=i<3?0:i==3?ease((u-.5)/.5):i<6?1:i==6?1-ease(u/.3):0;
 const ptsA=[],ptsB=[],rungs=[];
 for(let x=HX0;x<=HX1;x+=8){const s=x-HX0,th=phi+s*2*Math.PI/PER,bm=ob*Math.exp(-(((x-bx)/45)**2)),c=R*Math.cos(th)*(1-bm),d=R*Math.sin(th)*(1-bm);
  ptsA.push([x,HY+c-30*bm,d]);ptsB.push([x,HY-c+30*bm,-d])}
 for(let k=0;11+RS*k<HX1-HX0;k++){const x=HX0+11+RS*k,s=x-HX0,th=phi+s*2*Math.PI/PER,bm=ob*Math.exp(-(((x-bx)/45)**2));if(bm>0.25)continue;const c=R*Math.cos(th),d=R*Math.sin(th);
  rungs.push([x,HY+c,d,x,HY,x,HY-c,-d,seqD(k),comp(seqD(k)),1])}
 // mRNA: transcription form -> straight form
 const nb=i<4?0:clamp(Math.floor((bx-250)/9)+1,0,NB);
 const posT=j=>{const x=250+9*j,xx=Math.min(x,bx);return[xx,HY+16+((bx-xx)**2)/600]};
 const steps=[[S(9)+0.5,2.0],...[1,2,3].map(k=>[S(10)+(k-1)*1.2,1.2]),...[4,5,6].map(k=>[S(11)+(k-4)*1.1,1.1])];
 const sp=steps.map(([a,d])=>clamp((t-a)/d));
 let shift=0;for(const p of sp)shift+=42*ease((p-.6)/.4);
 const mv=i==6?ease((u-.3)/.7):i>6?1:0, mm=i==6?ease(u/.4):i>6?1:0;
 const lead=i<7?0:i==7?147*ease(u/.5):147;   // seg 7: mRNA slides so the ribosome assembles over AUG (codon being read is always at x=360)
 const my=lerp(470,765,mv), mx=360-shift+lead;
 const posS=j=>[mx-168+7+14*j,my];
 const pos=j=>{if(i<6)return posT(j);const a=posT(Math.min(j,NB-1)),b=posS(j);return[lerp(a[0],b[0],mm),lerp(a[1],b[1],mm)]};
 const vis=i<6?nb:NB+3;   // bases visible; +3 tail beads once processed
 const mpts=[];if(i>=6)mpts.push(pos(-1));for(let j=0;j<Math.min(vis,NB);j++)mpts.push(pos(j));if(i<6&&nb>0)mpts.push([bx,HY+16]);if(i>=6)mpts.push(pos(NB+2));
 const procOp=i==6?ease((u-.1)/.3):i>6?1:0;
 const stopOn=i>=12;
 const bases=[];for(let j=0;j<Math.min(vis,NB);j++){const p=pos(j);const c=(stopOn&&j>=21)?4:CI(SEQ[j]);bases.push([p[0],p[1],c])}
 const capP=pos(-1),tailP=[0,1,2].map(k=>pos(NB+k));
 // ribosome, tRNA, chain
 const rel=i<12?0:i==12?ease((u-.3)/.6):1;
 const rop=i<7?0:i==7?ease((u-.45)/.35):1, ryL=720-20*rel, ryS=800+15*rel;
 const ncompl=sp.filter(p=>p>=0.5).length;const cur=sp.findIndex(p=>p>0&&p<1);
 const tr=[];for(let k=0;k<7;k++){const p=sp[k];if(p<=0||p>=1)continue;let x,y,op;
  if(p<.4){const e=ease(p/.4);x=lerp(470,360,e);y=lerp(620,742,e);op=e}else if(p<.6){x=360;y=742;op=1}else{const e=ease((p-.6)/.4);x=lerp(360,250,e);y=lerp(742,650,e);op=1-e}
  tr.push([x,y,op,k])}
 const P=m=>[360+30*Math.sin(m*0.8),700-28*m];
 const bd=[];const latest=ncompl-1;const pl=latest>=0?sp[latest]:1;const b=ease((pl-.5)/.2);
 for(let j=0;j<ncompl;j++){let p;if(j==latest&&cur==latest)p=P(0);else{const m=(ncompl-1-j)-(cur==latest?1-b:0);p=P(m)}
  const cl=[470+24*Math.cos(j*2.4),600+24*Math.sin(j*2.4)];bd.push([lerp(p[0],cl[0],rel),lerp(p[1],cl[1],rel),j])}
 const glow=i==13?1:i==14?1-ease(u/.5):0;
 // ---- 2D draw
 set(pA,{d:dstr(ptsA)});set(pB,{d:dstr(ptsB)});rungG.innerHTML='';for(const r of rungs){el('line',{x1:r[0],y1:r1(r[1]),x2:r[3],y2:r[4],stroke:BC[r[8]==1?1:r[8]]},rungG);el('line',{x1:r[3],y1:r[4],x2:r[5],y2:r1(r[6]),stroke:BC[r[9]]},rungG)}
 set(polyE,{cx:bx,cy:r1(by),opacity:pop});pore.setAttribute('opacity',i==6?Math.min(ease(u/.3),1-ease((u-.8)/.2)):0);
 set(mrna,{d:dstr(mpts),opacity:nb>0||i>=6?1:0});mbG.innerHTML='';for(const [x,y,c] of bases)el('line',{x1:r1(x),y1:r1(y-3),x2:r1(x),y2:r1(y-14),stroke:BC[c]},mbG);
 set(capE,{cx:r1(capP[0]),cy:r1(capP[1]),opacity:procOp});tailE.forEach((e,k)=>set(e,{cx:r1(tailP[k][0]),cy:r1(tailP[k][1]),opacity:procOp}));
 set(riboL,{cx:360,cy:r1(ryL),opacity:rop});set(riboS,{cx:360,cy:r1(ryS),opacity:rop});
 trnas.forEach((g,n)=>{const v=tr[n];if(!v){g.setAttribute('opacity',0);return}g.setAttribute('transform',`translate(${r1(v[0])},${r1(v[1])})`);g.setAttribute('opacity',v[2]);g._b.setAttribute('fill',AC[v[3]])});
 beads.forEach((e,j)=>{const v=bd[j];if(!v){e.setAttribute('opacity',0);return}set(e,{cx:r1(v[0]),cy:r1(v[1]),opacity:1,stroke:glow>0?'#f1c232':'#fff'})});
 // mascot
 let mst;
 if(i<=2){const k=ease((t-0.2)/0.8);mst=[120,lerp(1000,880,k),0.7,1-ease((t-S(2))/.5),1];placeMascot(masc,mst[0],mst[1],mst[2],t,mst[3])}
 else if(i==11||i>=13){const base=i==11?[495,862,0.35]:[560,880,0.6];const w=i==11||i==14?Math.PI*2.2:0;const p=((t*w)%Math.PI)/Math.PI;const h=w?Math.sin(p*Math.PI)*28:0;const sq=w?1-0.22*Math.cos(2*Math.PI*p):1;
  placeMascot(masc,base[0],base[1]-h*base[2]/0.6,base[2],t,i==11?ease(u/.3):i==13?ease(u/.3):1,sq)}
 else masc.setAttribute('opacity',0);
 // ---- labels (screen space)
 place(nucT,360,300,i<=2?(i==2?1:0.9):0);place(promT,250,470,i==3?ease(u/.3):0);place(polT,bx,HY-62,i==3?ease((u-.3)/.3):i==4?1-ease(u/.4):0);
 place(tmplT,300,HY+108,i==4?ease(u/.3):i==5?1-ease(u/.4):0);place(mT,232,HY+34,i==4?ease((u-.4)/.3):i==5?1:i==6?1-ease(u/.3):0);
 legend.setAttribute('opacity',i==5?ease(u/.3):i==6?1-ease(u/.3):0);
 const prT=i==6?Math.min(ease((u-.15)/.25),1-ease((u-.75)/.2)):0;place(capT,capP[0],capP[1]-22,prT);place(tailT,tailP[2][0]-14,tailP[2][1]+30,prT);place(poreT,470,572,i==6?Math.min(ease((u-.4)/.3),1-ease((u-.9)/.1)):0);
 place(riboT,360,860,i==7?ease((u-.6)/.3):i==8?1-ease(u/.4):0);
 codonL.forEach((l,k)=>{const a=pos(3*k),bq=pos(3*k+2);const on=i==8&&u*2.2>k*0.25;const [x1,y1]=V(a[0],a[1]+16),[x2]=V(bq[0],0);set(l,{x1:r1(x1),y1:r1(y1),x2:r1(x2),y2:r1(y1),opacity:i==8?(on?1:0.25):0,stroke:on?'#e8803f':'#b9a58c'})});
 letters.forEach((e,j)=>{const p=pos(j);const [sx,sy]=V(p[0],p[1]-22);set(e,{x:r1(sx),y:r1(sy),'font-size':r1(13*VW.z),opacity:i>=7||(i==6&&u>.7)?1:0,fill:(stopOn&&j>=21)?BC[4]:BC[CI(SEQ[j])]})});
 place(startT,360,805,i==9?ease(u/.3):i==10?1-ease(u/.4):0);
 {const op=i==10?ease(u/.3):i==11?1-ease(u/.4):0;const d=tr.find(v=>v[1]>700&&v[0]>330&&v[0]<390);const tx=d?d[0]:360,ty=d?d[1]:742;
  place(trT,470,690,op);const [ax,ay]=V(tx+12,ty-20),[bx2,by2]=V(440,690);trA.at(bx2-20,by2+6,ax+6,ay,op);
  place(antiT,480,790,op);const [cx2,cy2]=V(tx+16,ty+28),[dx2,dy2]=V(448,790);antiA.at(dx2-20,dy2-6,cx2+6,cy2,op)}
 place(pepT,250,640,i==11?ease(u/.3):i==12?1-ease(u/.4):0);
 place(stopT,360,810,i==12?ease(u/.3):i==13?1-ease(u/.4):0);
 place(protT,470,648,i==13?ease(u/.3):i==14?1-ease(u/.4):0);
 pA1.forEach((p,k)=>{p.g.setAttribute('opacity',i<=13?1:0);p.on(i==1?u*2.4>k+0.5:(k==0?i>=2&&i<=6:i>=7&&i<=13))});
 pA2.forEach((p,k)=>{p.g.setAttribute('opacity',i==14?1:0);p.on(i==14&&u*3.6>k+0.5)});
 const P3=p=>[r1(p[0]),r1(p[1]),r1(p[2]||0)];
 ST={view:[r1(VW.z*100)/100,r1(VW.cx),r1(VW.cy)],nucGlow:r1(nucGlow),pore:+pore.getAttribute('opacity'),poly:[bx,r1(by),r1(pop)],pA:ptsA.map(P3),pB:ptsB.map(P3),rungs:rungs.map(r=>r.map((v,k)=>k<8?r1(v):v)),
  mrna:mpts.map(p=>[r1(p[0]),r1(p[1])]),bases:bases.map(b=>[r1(b[0]),r1(b[1]),b[2]]),cap:[r1(capP[0]),r1(capP[1]),r1(procOp)],tail:tailP.map(p=>[r1(p[0]),r1(p[1]),r1(procOp)]),
  ribo:[360,r1(ryL),r1(ryS),r1(rop)],trna:tr.map(v=>[r1(v[0]),r1(v[1]),r1(v[2]),v[3]]),beads:bd.map(v=>[r1(v[0]),r1(v[1]),v[2]]),glow:r1(glow),
  masc:masc.getAttribute('opacity')==='0'?[0,0,0,0,1,1]:masc._st};}
