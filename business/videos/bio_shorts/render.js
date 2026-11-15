const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const [,,scene,out,fps0,only,mode]=process.argv;const fps=+fps0||24;
 const html=fs.readFileSync(__dirname+'/page.html','utf8').replace('SCENE',scene);fs.writeFileSync(__dirname+'/_'+scene+'.html',html);
 const b=await chromium.launch();const p=await b.newPage({viewport:{width:720,height:1280}});
 p.on('pageerror',e=>{console.error('PAGEERR',e.message);process.exit(1)});
 await p.goto('file://'+__dirname+'/_'+scene+'.html'+(mode=='overlay'?'#overlay':''));await p.evaluate(()=>document.fonts.ready);
 const T=await p.evaluate('TOTAL');fs.mkdirSync(out,{recursive:true});
 const times=only?only.split(',').map(Number):[...Array(Math.ceil(T*fps)).keys()].map(i=>i/fps);
 let i=0;const states=[];for(const t of times){await p.evaluate(t=>seek(t),t);if(mode=='state'){states.push(await p.evaluate(()=>ST));i++}else await p.screenshot({path:`${out}/f${String(i++).padStart(4,'0')}.png`,omitBackground:mode=='overlay'});}
 if(mode=='state')fs.writeFileSync(out+'/state.json',JSON.stringify({fps,states}));
 await b.close();console.log('frames',i,'T',T.toFixed(2))})();
