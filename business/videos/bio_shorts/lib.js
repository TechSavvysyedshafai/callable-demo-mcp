const W=720,H=1280,NS='http://www.w3.org/2000/svg';
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const ease=x=>{x=clamp(x);return x*x*(3-2*x)};
const lerp=(a,b,u)=>a+(b-a)*u;
const svg=document.getElementById('s'), cap=document.getElementById('cap');
const OVER=location.hash=='#overlay';const DIA=[];window.ST={};
function dia(e){DIA.push(e);return e}
function finishOverlay(){if(!OVER)return;document.body.style.background='transparent';document.documentElement.style.background='transparent';svg.firstChild.style.display='none';for(const g of DIA){[g,...g.querySelectorAll('*')].forEach(e=>{if(e.tagName!='text'&&e.tagName!='g')e.style.display='none'})}}
function el(tag,attrs,parent){const e=document.createElementNS(NS,tag);for(const k in attrs)e.setAttribute(k,attrs[k]);(parent||svg).appendChild(e);return e}
function txt(s,attrs,parent){const e=el('text',Object.assign({'font-family':'Inter, sans-serif'},attrs),parent);e.textContent=s;return e}
function set(e,attrs){for(const k in attrs)e.setAttribute(k,attrs[k])}
let SEG=[],STARTS=[],TOTAL=0;
function setSegments(list){SEG=list;let t=0;STARTS=list.map(s=>{const a=t;t+=s.d;return a});TOTAL=t+0.6;window.TOTAL=TOTAL}
function segAt(t){let i=0;for(let k=0;k<SEG.length;k++)if(t>=STARTS[k])i=k;return i}
function segU(i,t){return clamp((t-STARTS[i])/SEG[i].d)}
function header(series,title){el('rect',{x:0,y:0,width:W,height:H,fill:'#f6f1e8'});
 txt(series,{x:360,y:66,'text-anchor':'middle','font-size':22,'font-weight':600,'letter-spacing':3,fill:'#8a7f72'});
 txt(title,{x:360,y:120,'text-anchor':'middle','font-size':44,'font-weight':700,fill:'#1f2430'});
 window._bar=el('rect',{x:0,y:1268,width:0,height:12,fill:'#e8803f'});}
function caption(t){const i=segAt(t),u=t-STARTS[i];const s=SEG[i];
 cap.innerHTML='<span>'+s.c.replace(/\*(.+?)\*/g,'<b>$1</b>')+'</span>';
 const a=ease(u/0.25);cap.style.opacity=t>TOTAL-0.6?1:a;cap.style.transform=`translateY(${(1-a)*18}px)`;
 cap.style.fontSize=(s.hook?54:44)+'px';_bar.setAttribute('width',W*clamp(t/TOTAL));}
function makeMascot(parent){const g=el('g',{},parent);const c='#e8803f',d='#c9652a';
 el('rect',{x:-78,y:-8,width:20,height:18,fill:d,rx:2},g);el('rect',{x:58,y:-8,width:20,height:18,fill:d,rx:2},g);
 for(const x of[-46,-21,4,29])el('rect',{x,y:30,width:16,height:12,fill:d,rx:2},g);
 el('rect',{x:-60,y:-36,width:120,height:70,fill:c,rx:7},g);
 const eyes=el('g',{},g);el('rect',{x:-24,y:-16,width:10,height:20,fill:'#222',rx:2},eyes);el('rect',{x:14,y:-16,width:10,height:20,fill:'#222',rx:2},eyes);
 g._eyes=eyes;return g}
function placeMascot(g,x,y,s,t,op=1){const b=((t%3.1)<0.12)?0.1:1;g._st=[x,y,s,op,b];
 g._eyes.setAttribute('transform',`translate(0,-6) scale(1,${b}) translate(0,6)`);
 g.setAttribute('transform',`translate(${x},${y}) scale(${s})`);g.setAttribute('opacity',op)}
function pills(labels,y,parent){const n=labels.length,gap=12,w=(W-80-gap*(n-1))/n;return labels.map((l,k)=>{const g=el('g',{},parent);
 const r=el('rect',{x:40+k*(w+gap),y:y-26,width:w,height:52,rx:26,fill:'#e9e1d4'},g);
 const tx=txt(l,{x:40+k*(w+gap)+w/2,y:y+8,'text-anchor':'middle','font-size':21,'font-weight':600,fill:'#6b6258'},g);
 return {g,on(v){r.setAttribute('fill',v?'#e8803f':'#e9e1d4');tx.setAttribute('fill',v?'#fff':'#6b6258')}}})}
function poly(pts,f){// point at fraction f along polyline
 let L=[0];for(let i=1;i<pts.length;i++)L.push(L[i-1]+Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]));
 let d=f*L[L.length-1];for(let i=1;i<pts.length;i++)if(d<=L[i]||i==pts.length-1){const u=(d-L[i-1])/(L[i]-L[i-1]||1);return[lerp(pts[i-1][0],pts[i][0],u),lerp(pts[i-1][1],pts[i][1],u)]}}
function arrow(parent,color){const g=el('g',{},parent);const l=el('line',{stroke:color,'stroke-width':5,'stroke-linecap':'round'},g);const h=el('path',{fill:color},g);
 g.at=(x1,y1,x2,y2,op)=>{set(l,{x1,y1,x2,y2});const a=Math.atan2(y2-y1,x2-x1),s=13;
  h.setAttribute('d',`M${x2+Math.cos(a)*4},${y2+Math.sin(a)*4} L${x2-s*Math.cos(a-0.5)},${y2-s*Math.sin(a-0.5)} L${x2-s*Math.cos(a+0.5)},${y2-s*Math.sin(a+0.5)}Z`);g.setAttribute('opacity',op)};return g}
