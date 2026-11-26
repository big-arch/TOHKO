(() => {
  'use strict';
  const seed=document.getElementById('editorial-updates-data');if(!seed)return;
  let items;try{items=JSON.parse(seed.textContent);}catch{return;}
  document.querySelectorAll('[data-editorial-news]').forEach(a=>a.addEventListener('click',event=>{
    if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||!window.TonkoReader)return;
    const item=items.find(p=>p.id===a.dataset.editorialNews);if(!item)return;
    event.preventDefault();window.TonkoReader.open(item);
  }));
  const fromUrl=()=>{const id=new URLSearchParams(location.search).get('news');const item=items.find(p=>p.id===id);if(item)window.TonkoReader?.open(item,true);else if(!id)window.TonkoReader?.close();};
  fromUrl();addEventListener('popstate',fromUrl);
})();
