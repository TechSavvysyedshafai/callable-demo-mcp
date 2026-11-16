setSegments([
 {c:'How does one DNA become *two identical copies*?',d:3.4,hook:1},
 {c:'E. coli copies about *2,000 base pairs every second*.',d:3.2,hook:1},
 {c:'It starts at one spot: the *origin of replication*.',d:3.0},
 {c:'The enzyme *helicase* unzips the two strands.',d:3.6},
 {c:'Each old strand now acts as a *template*.',d:3.0},
 {c:'*DNA polymerase* adds new matching bases: A with T, G with C.',d:4.0},
 {c:'But polymerase can only build in *one direction: 5′ → 3′*.',d:3.6},
 {c:'On one strand it builds smoothly: the *leading strand*.',d:3.2},
 {c:'On the other, it builds in short pieces: the *lagging strand*.',d:3.4},
 {c:'These short pieces are *Okazaki fragments*.',d:2.8},
 {c:'*DNA ligase* joins them into one strand.',d:3.2},
 {c:'Result: two DNA molecules, each with *one old and one new strand*.',d:4.0},
 {c:'That’s why it’s called *semi-conservative replication*.',d:3.2},
 {c:'Remember: *Helicase opens, Polymerase builds, Ligase joins.*',d:4.4},
 {c:'Follow for the next chapter.',d:2.6},
]);
header('BIOLOGY IN 50 SECONDS · CLASS 12','DNA Replication');
// geometry constants (screen px). Parent duplex runs from YB (bottom) up to the fork; s = distance from the bottom.
const YB=900,YT=240,LT=660,R=22,PER=110,RS=22,ALPHA=Math.PI/180*22,KS=1.08,NF=7,FL=LT/NF;
const BC=['#e0663a','#3b82c4','#2e9e6b','#e6b422'];            // A T G C
const seq=i=>(((Math.imul(i,0x9E3779B1)>>>0)>>>13)%4), comp=c=>c^1;
const OLD='#3b4a5c',NEW='#e8803f';
const dna=dia(el('g',{}));
const rungG=el('g',{'stroke-width':7,'stroke-linecap':'round'},dna);
const bb=c=>el('path',{fill:'none',stroke:c,'stroke-width':9,'stroke-linecap':'round','stroke-linejoin':'round'},dna);
const pB=bb(OLD),pA=bb(OLD),oL=bb(OLD),oR=bb(OLD),nL=bb(NEW),nR=bb(NEW);
const origin=dia(el('circle',{r:16,fill:'#e6b422',stroke:'#fff','stroke-width':4}));
const heli=dia(el('circle',{r:28,fill:'#3b82c4',stroke:'#fff','stroke-width':4}));
const polys=[0,1].map(()=>dia(el('circle',{r:20,fill:'#2e9e6b',stroke:'#fff','stroke-width':3})));
const ligs=[...Array(6)].map(()=>dia(el('circle',{r:10,fill:'#8e5aa8'})));
// overlay text and widgets (stay visible in overlay mode)
const lab=(s,attrs)=>txt(s,Object.assign({'font-size':21,'font-weight':600,fill:'#2b2b2b','text-anchor':'middle'},attrs));
const counter=txt('',{x:560,y:330,'text-anchor':'middle','font-size':56,'font-weight':800,fill:'#1f2430'});
const counterT=lab('base pairs / second',{x:560,y:362,'font-size':19,fill:'#8a7f72'});
const originT=lab('origin of replication',{x:360,y:212});
const heliT=lab('helicase',{fill:'#2b5f94'});
const tmplT=[lab('template',{}),lab('template',{})];
const dirT=lab('5′ → 3′ only',{fill:'#1f6b45'}); const dirA=arrow(svg,'#1f6b45');
const leadT=lab('leading strand',{x:360,y:318,fill:'#1f6b45'}), lagT=lab('lagging strand',{x:360,y:318,fill:'#1f6b45'}), okaT=lab('Okazaki fragments',{x:360,y:318,fill:'#7a3f99'}), ligT=lab('ligase',{fill:'#6b3d85'});
const leadA=arrow(svg,'#1f6b45'), lagA=arrow(svg,'#1f6b45'), okaA=arrow(svg,'#7a3f99');
const oldnew=[230,490].map(x=>{const g=el('g',{});txt('old',{x:x-27,y:214,'text-anchor':'middle','font-size':21,'font-weight':700,fill:OLD},g);txt('+',{x,y:214,'text-anchor':'middle','font-size':21,'font-weight':700,fill:'#8a7f72'},g);txt('new',{x:x+30,y:214,'text-anchor':'middle','font-size':21,'font-weight':700,fill:NEW},g);return g});
const legend=el('g',{});[['A',0,'T',1,850],['G',2,'C',3,892]].forEach(([a,ca,b,cb,y])=>{txt(a,{x:560,y:y+8,'text-anchor':'middle','font-size':24,'font-weight':800,fill:BC[ca]},legend);el('line',{x1:580,x2:612,y1:y,y2:y,stroke:'#b9a58c','stroke-width':4},legend);el('circle',{cx:596,cy:y,r:7,fill:BC[ca]},legend);el('circle',{cx:596,cy:y,r:7,fill:BC[cb],'clip-path':'inset(0 0 0 50%)'},legend);txt(b,{x:632,y:y+8,'text-anchor':'middle','font-size':24,'font-weight':800,fill:BC[cb]},legend)});
const pl=pills(['Helicase','Polymerase','Ligase'],925);
const masc=dia(makeMascot());finishOverlay();
const FY=[[240,240],[240,240],[240,240],[240,440],[440,470],[470,550],[550,610],[610,680],[680,790],[790,820],[820,860],[860,900],[900,900],[900,900],[900,900]];
const r1=v=>Math.round(v*10)/10;
const d=pts=>pts.length?'M'+pts.map(p=>r1(p[0])+','+r1(p[1])).join('L'):'';
function seek(t){caption(t);const i=segAt(t),u=segU(i,t);
 const yf=lerp(FY[i][0],FY[i][1],i==3?ease(u):i==11?clamp(u/.4):u);
 const st=i<11?0:i==11?ease((u-.4)/.6):1;           // arms straighten into two vertical duplexes
 const lig=i<10?0:i==10?ease(u/.8):1;                // ligase closes the gaps
 const Lp=YB-yf, phi=0.5*t, t5=STARTS[5];
 // parent duplex
 const ptsA=[],ptsB=[],rungs=[];
 const ss=[];for(let s=0;s<Lp;s+=8)ss.push(s);if(Lp>0)ss.push(Lp);
 for(const s of ss){const th=phi+s*2*Math.PI/PER;ptsA.push([360+R*Math.cos(th),YB-s,R*Math.sin(th)]);ptsB.push([360-R*Math.cos(th),YB-s,-R*Math.sin(th)])}
 for(let k=0;11+RS*k<Lp;k++){const s=11+RS*k,th=phi+s*2*Math.PI/PER,c=Math.cos(th),sn=Math.sin(th);rungs.push([360+R*c,YB-s,R*sn,360,YB-s,360-R*c,YB-s,-R*sn,seq(k),comp(seq(k)),1])}
 // arms: k=0 left (leading), k=1 right (lagging)
 const arms=[0,1].map(k=>{const sg=k?1:-1,a=ALPHA*(1-st),dir=[sg*Math.sin(a),-Math.cos(a)],n=[-dir[1],dir[0]],F=[lerp(360,360+sg*130,st),yf],K=lerp(KS,1,st);
  const ax=s=>[F[0]+dir[0]*(s-Lp)*K,F[1]+dir[1]*(s-Lp)*K], th=s=>phi+s*2*Math.PI/PER+(k?Math.PI:0);
  const oldP=s=>{const p=ax(s),c=Math.cos(th(s));return[p[0]+n[0]*R*c,p[1]+n[1]*R*c,R*Math.sin(th(s))]};
  const newP=s=>{const p=ax(s),c=Math.cos(th(s));return[p[0]-n[0]*R*c,p[1]-n[1]*R*c,-R*Math.sin(th(s))]};
  let iv=[],front=null,prog=[];
  if(t>=t5&&Lp<LT){
   if(k==0){const sL=Math.max(Lp+30*(1-st),LT-260*(t-t5));if(sL<LT-2){iv=[[sL,LT]];front=sL}}
   else{const gap=12*(1-lig);
    for(let j=0;j<NF;j++){const lo0=LT-(j+1)*FL,hi0=LT-j*FL;const p=clamp(Math.min((lo0-Lp+40)/40,(t-t5)*1.6-j*0.45));prog.push(p);if(p<=0)continue;
     const lo=Math.max(lo0+gap,Lp+6),hi=lo0+gap+p*(hi0-lo0-gap);if(hi>lo+2)iv.push([lo,hi]);if(p<1)front=hi;else if(front===null&&j==NF-1)front=hi}
    if(front===null&&iv.length)front=iv[iv.length-1][1];
    iv.sort((a,b)=>a[0]-b[0]);const m=[];for(const v of iv){if(m.length&&v[0]-m[m.length-1][1]<0.6)m[m.length-1][1]=v[1];else m.push([...v])}iv=m}}
  const old=[],nw=[];
  if(Lp<LT){const ss=[];for(let s=Lp;s<LT;s+=8)ss.push(s);ss.push(LT);for(const s of ss)old.push(oldP(s))}
  for(const [lo,hi] of iv){const pts=[];for(let s=lo;s<hi;s+=8)pts.push(newP(s));pts.push(newP(hi));nw.push(pts)}
  for(let j=0;11+RS*j<LT;j++){const s=11+RS*j;if(s<Lp)continue;const p=ax(s),o=oldP(s),q=newP(s);const has=iv.some(([lo,hi])=>s>=lo&&s<=hi)?1:0;
   const co=k?comp(seq(j)):seq(j);rungs.push([o[0],o[1],o[2],p[0],p[1],q[0],q[1],q[2],co,comp(co),has])}
  return {dir,n,F,ax,oldP,newP,iv,old,nw,front,prog,sg}});
 // 2D drawing
 set(pA,{d:d(ptsA)});set(pB,{d:d(ptsB)});set(oL,{d:d(arms[0].old)});set(oR,{d:d(arms[1].old)});
 set(nL,{d:arms[0].nw.map(d).join(' ')});set(nR,{d:arms[1].nw.map(d).join(' ')});
 rungG.innerHTML='';for(const r of rungs){el('line',{x1:r1(r[0]),y1:r1(r[1]),x2:r1(r[3]),y2:r1(r[4]),stroke:BC[r[8]]},rungG);if(r[10])el('line',{x1:r1(r[3]),y1:r1(r[4]),x2:r1(r[5]),y2:r1(r[6]),stroke:BC[r[9]]},rungG)}
 // enzymes
 const hop=i<3?0:i==3?ease(u/.3):i<11?1:i==11?1-ease(u/.4):0;set(heli,{cx:360,cy:yf,opacity:hop});
 const pop=t<t5?0:i==5?ease(u/.3):i<11?1:i==11?1-ease(u/.4):0;
 const ppos=arms.map(a=>a.front===null?a.ax(Lp):a.newP(a.front));
 polys.forEach((p,k)=>set(p,{cx:r1(ppos[k][0]),cy:r1(ppos[k][1]),opacity:pop}));
 const lop=i==10?(u<.75?ease(u/.3):1-ease((u-.75)/.25)):0;const lpos=[];
 ligs.forEach((g,j)=>{const s=LT-(j+1)*FL;const ok=arms[1].prog[j]>=1&&arms[1].prog[j+1]>0;const p=arms[1].newP(s);const op=ok?lop:0;lpos.push([r1(p[0]),r1(p[1]),op]);set(g,{cx:r1(p[0]),cy:r1(p[1]),opacity:op,r:10+3*Math.sin(t*12)})});
 const oop=i==2?ease(u/.3):i==3?1-ease(u/.5):0;set(origin,{cx:360,cy:YT,opacity:oop,r:16+3*Math.sin(t*6)});
 // labels
 const cop=i==1?ease(u/.3):i==2?1-ease(u/.4):0;counter.textContent=Math.round(2000*ease(i==1?u/1.5:1)).toLocaleString('en-US');set(counter,{opacity:cop});set(counterT,{opacity:cop});
 set(originT,{opacity:oop});
 set(heliT,{x:440,y:yf+8,opacity:i==3?ease((u-.2)/.3):0});
 const top=i==4?ease(u/.3):i==5?1-ease(u/.4):0;arms.forEach((a,k)=>{const m=a.ax((Lp+LT)/2);set(tmplT[k],{x:r1(m[0]+a.sg*85),y:r1(m[1]+6),opacity:top})});
 legend.setAttribute('opacity',i==5?ease(u/.3):i==6?1:i==7?1-ease(u/.4):0);
 {const a=arms[0],dop=i==6?ease(u/.3):i==7?1-ease(u/.4):0;const s=a.front===null?Lp+40:a.front;const b=a.ax(s);const o=[-a.n[0]*60,-a.n[1]*60];
  dirA.at(b[0]+a.dir[0]*70+o[0],b[1]+a.dir[1]*70+o[1],b[0]-a.dir[0]*25+o[0],b[1]-a.dir[1]*25+o[1],dop);set(dirT,{x:r1(b[0]+a.dir[0]*25+o[0]*1.9),y:r1(b[1]+a.dir[1]*25+o[1]*1.9+8),opacity:dop})}
 {const a=arms[0],m=a.ax((Lp+LT)/2),op=i==7?ease(u/.3):i==8?1-ease(u/.4):0;set(leadT,{opacity:op});leadA.at(300,336,r1(m[0]+a.n[0]*34),r1(m[1]+a.n[1]*34),op)}
 {const a=arms[1],m=a.ax((Lp+LT)/2);const o1=i==8?ease(u/.3):i==9?1-ease(u/.4):0,o2=i==9?ease(u/.3):i==10?1-ease(u/.4):0;set(lagT,{opacity:o1});set(okaT,{opacity:o2});
  lagA.at(420,336,r1(m[0]-a.n[0]*34),r1(m[1]-a.n[1]*34),o1);okaA.at(420,336,r1(m[0]-a.n[0]*34),r1(m[1]-a.n[1]*34),o2);
  const g=a.ax(LT-FL);set(ligT,{x:r1(g[0]-a.n[0]*80),y:r1(g[1]-a.n[1]*80+8),opacity:i==10?ease(u/.3):i==11?1-ease(u/.4):0})}
 const onop=i==11?ease((u-.7)/.3):i==12?1:i==13?1-ease(u/.4):0;oldnew.forEach(g=>g.setAttribute('opacity',onop));
 pl.forEach((p,k)=>p.on(i==13?u*3.6>k+0.5:i==14));
 // mascot
 if(i<=2)placeMascot(masc,150,790-(i==0?Math.abs(Math.sin(t*4))*18:0),0.8,t,1-ease((t-STARTS[2])/.5));
 else if(i>=12)placeMascot(masc,360,600+(i==12?Math.sin(u*Math.PI*4)*10:0)-(i==14?Math.abs(Math.sin(t*5))*24:0),0.6,t,i==12?ease(u/.3):1);
 else masc.setAttribute('opacity',0);
 const P3=p=>[r1(p[0]),r1(p[1]),r1(p[2])];
 ST={pA:ptsA.map(P3),pB:ptsB.map(P3),arms:arms.map(a=>({old:a.old.map(P3),nw:a.nw.map(l=>l.map(P3))})),rungs:rungs.map(r=>r.map((v,k)=>k<8?r1(v):v)),
  heli:[360,r1(yf),r1(hop)],poly:ppos.map(p=>[r1(p[0]),r1(p[1]),r1(pop)]),lig:lpos,origin:[360,YT,r1(oop)],
  masc:masc.getAttribute('opacity')==='0'?[0,0,0,0,1]:masc._st};}
