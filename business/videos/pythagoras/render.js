// usage: node render.js A|B outdir fps seconds
const {chromium}=require('playwright');
(async()=>{
  const [,, which, out, fps, secs]=process.argv; const T=+secs, F=+fps;
  const fs=require('fs'); fs.mkdirSync(out,{recursive:true});
  const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1080,height:1920}});
  await p.goto('file://'+__dirname+'/scene.html');
  const n=Math.round(T*F);
  for(let i=0;i<n;i++){
    await p.evaluate(([w,t,T])=>window.frame(w,t,T),[which,i/F,T]);
    await p.screenshot({path:`${out}/f${String(i).padStart(5,'0')}.jpg`,type:'jpeg',quality:88});
  }
  await b.close(); console.log('frames',n);
})();
