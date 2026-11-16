/* Storage failure must never prevent playback. Progress is local to this browser. */
((root) => {
  'use strict';
  const key='tonko-video-progress-v1';
  let sessionMode;
  const clean=(seconds,duration)=>Number.isFinite(seconds)&&seconds>=0&&Number.isFinite(duration)&&duration>0&&seconds<duration-3?Math.floor(seconds):0;
  const read=()=>{try{const v=JSON.parse(root.localStorage.getItem(key)||'{}');return v&&typeof v==='object'&&!Array.isArray(v)?v:{};}catch{return {};}};
  const api={
    clean,
    get(id){const v=read()[id];return v?clean(v.seconds,v.duration):0;},
    save(id,seconds,duration){
      if(!Number.isFinite(seconds)||!Number.isFinite(duration)||duration<=0)return;
      try{const all=read();all[id]={seconds:clean(seconds,duration),duration,at:Date.now()};const bounded=Object.fromEntries(Object.entries(all).sort((a,b)=>b[1].at-a[1].at).slice(0,80));root.localStorage.setItem(key,JSON.stringify(bounded));}catch{}
    },
    mode(){if(sessionMode)return sessionMode;try{return root.localStorage.getItem('tonko-youtube-mode')==='standard'?'standard':'private';}catch{return 'private';}},
    setMode(mode){sessionMode=mode==='standard'?'standard':'private';try{root.localStorage.setItem('tonko-youtube-mode',sessionMode);}catch{}}
  };
  root.TonkoVideoMemory=api;
  if(typeof module!=='undefined')module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
