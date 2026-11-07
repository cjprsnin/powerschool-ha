/* powerschool-v2-card — app-style with 14d grade sparklines + trends */
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&','<':'<','>':'>','"':'"',"'":'&#39;'}[c]));
const LET=[[93,'A'],[90,'A-'],[87,'B+'],[83,'B'],[80,'B-'],[77,'C+'],[73,'C'],[70,'C-'],[67,'D+'],[63,'D'],[60,'D-']];
const letter=p=>{if(p==null||isNaN(p))return '\u2013';const r=Math.round(p);for(const [m,l] of LET)if(r>=m)return l;return 'F';};
const gcls=p=>p==null?'':(p>=90?'ga':p>=80?'gb':p>=70?'gc':'gf');
const fmt=v=>v==null?'\u2013':String(Math.round(v*100)/100);
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
console.info('powerschool-v2-card loaded (sparklines)');
if(!customElements.get('powerschool-v2-card')){
  class PowerSchoolV2Card extends HTMLElement{
    constructor(){super();this.attachShadow({mode:'open'});this._view={t:'home'};this._trend={};this._spark={};this._trendLoaded=false;this._trendLoading=false;this._sig='';this._refreshing=false;}
    setConfig(c){this._config=Object.assign({},c);this._view={t:'home'};this._sig='';this._trend={};this._spark={};this._trendLoaded=false;this._trendLoading=false;}
    set hass(h){this._hass=h;const sig=this._states().map(s=>s.entity_id+s.last_updated).join('|');if(sig!==this._sig){this._sig=sig;this._render();this._loadTrends();}}
    getCardSize(){return this._config&&this._config.compact?6:10;}
    static getStubConfig(){return{student:'Trent'};}
    _isCourseSensor(s){const a=s.attributes||{};if(!s.entity_id.startsWith('sensor.')||!('student' in a))return false;if('window_days' in a||'attendance_status' in a)return false;const eid=s.entity_id.toLowerCase();if(/due_soon|upcoming_assignments|grade_average|missing_assignments|late_assignments|_status$|absences|tardies/.test(eid))return false;return 'section_id' in a||'missing_homework' in a||'assignment_status' in a;}
    _states(){const stu=(this._config.student||'').toLowerCase();const hide=!this._config.show_empty;
      return Object.values(this._hass.states).filter(s=>{
        if(!this._isCourseSensor(s))return false;
        const a=s.attributes||{};const name=String(a.student||'').toLowerCase();const eid=s.entity_id.toLowerCase();
        if(stu&&name!==stu&&!eid.includes(stu.replace(/\s+/g,'_')))return false;
        if(hide&&(s.state==='unknown'||s.state==='unavailable'||s.state===''))return false;
        return true;
      });
    }
  }
  customElements.define('powerschool-v2-card',PowerSchoolV2Card);
}
