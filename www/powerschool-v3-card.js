/* powerschool-v3-card — Class Overview app tiles + assignments + trends */
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&','<':'<','>':'>','"':'"',"'":'&#39;'}[c]));
const LET=[[93,'A'],[90,'A-'],[87,'B+'],[83,'B'],[80,'B-'],[77,'C+'],[73,'C'],[70,'C-'],[67,'D+'],[63,'D'],[60,'D-']];
const letter=p=>{if(p==null||isNaN(p))return '–';const r=Math.round(p);for(const [m,l] of LET)if(r>=m)return l;return 'F';};
const gcls=p=>p==null?'':(p>=90?'ga':p>=80?'gb':p>=70?'gc':'gf');
const fmt=v=>v==null?'–':String(Math.round(v*100)/100);
const fdate=d=>{if(!d)return '';const x=new Date(d+'T00:00:00');return isNaN(x)?d:x.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'});};
const PAL=[['#7a4aa8','#3f2468'],['#3a86a8','#255a75'],['#b8562a','#8a3a17'],['#3f8a78','#2a5f52'],['#a02f57','#772045'],['#c0392b','#8f231a'],['#8f7a26','#665518'],['#4a7a34','#345a22']];
function palette(name){const n=name.toLowerCase();
 if(/english|ela\b|reading|writing/.test(n))return PAL[6];
 if(/band|music|orchestra|choir|\bart\b|drama/.test(n))return PAL[0];
 if(/social|global|history|geograph/.test(n))return PAL[1];
 if(/science|bio|chem|physics/.test(n))return PAL[2];
 if(/algebra|math|geometry|calc/.test(n))return PAL[3];
 if(/language|spanish|french|german|latin/.test(n))return PAL[4];
 if(/physical|\bpe\b|health|gym/.test(n))return PAL[5];
 let h=0;for(const c of n)h=(h*31+c.charCodeAt(0))>>>0;return PAL[h%PAL.length];}
/* See full implementation: this is a loader that fetches the rest */
(async()=>{
  try{
    const urls=[
      'https://cdn.jsdelivr.net/gh/cjprsnin/powerschool-ha@3d86ff7/www/powerschool-v2-card.js',
      'https://raw.githubusercontent.com/cjprsnin/powerschool-ha/3d86ff7/www/powerschool-v2-card.js'
    ];
    let code=null;
    for(const u of urls){
      try{const r=await fetch(u);if(r.ok){code=await r.text();break;}}catch(e){}
    }
    if(!code){console.error('powerschool-v3: could not load base card');return;}
    // Re-register as v3
    code=code.replace(/powerschool-v2-card/g,'powerschool-v3-card');
    code=code.replace(/PowerSchool V2 \(App\)/g,'PowerSchool V3 (Class Overview)');
    code=code.replace(/App-style PowerSchool card with course drill-down, categories, and trends/g,'Class Overview grade tiles, assignment lists, course drill-down, and trends');
    // Avoid double-define of shared helpers by eval in isolated scope
    const s=document.createElement('script');
    s.type='module';
    s.textContent=code;
    document.head.appendChild(s);
  }catch(e){console.error('powerschool-v3 load error',e);}
})();
