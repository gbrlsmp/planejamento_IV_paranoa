"use strict";
// SIRGAS 2000 / UTM 23S: elipsoide GRS80. Só a cartografia usa estas funções.
const FitopolisDados = (() => {
  const a = 6378137, e2 = 0.006694380022900787, ep2 = e2 / (1 - e2), k0 = .9996, rad = Math.PI / 180;
  function utmForward(lng, lat) {
    const phi = lat * rad, lam = (lng + 45) * rad, s = Math.sin(phi), c = Math.cos(phi), t = Math.tan(phi);
    const n = a / Math.sqrt(1 - e2 * s * s), T = t * t, C = ep2 * c * c, A = c * lam;
    const M = a * ((1 - e2/4 - 3*e2**2/64 - 5*e2**3/256)*phi - (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024)*Math.sin(2*phi) + (15*e2**2/256 + 45*e2**3/1024)*Math.sin(4*phi) - 35*e2**3/3072*Math.sin(6*phi));
    return [500000 + k0*n*(A + (1-T+C)*A**3/6 + (5-18*T+T*T+72*C-58*ep2)*A**5/120),
      10000000 + k0*(M + n*t*(A*A/2 + (5-T+9*C+4*C*C)*A**4/24 + (61-58*T+T*T+600*C-330*ep2)*A**6/720))];
  }
  function utmInverse(x, y) {
    const mu = (y-10000000)/k0/(a*(1-e2/4-3*e2**2/64-5*e2**3/256));
    const e1 = (1-Math.sqrt(1-e2))/(1+Math.sqrt(1-e2));
    const phi = mu + (3*e1/2-27*e1**3/32)*Math.sin(2*mu) + (21*e1**2/16-55*e1**4/32)*Math.sin(4*mu) + 151*e1**3/96*Math.sin(6*mu) + 1097*e1**4/512*Math.sin(8*mu);
    const s=Math.sin(phi), c=Math.cos(phi), t=Math.tan(phi), N=a/Math.sqrt(1-e2*s*s), R=a*(1-e2)/(1-e2*s*s)**1.5;
    const T=t*t, C=ep2*c*c, D=(x-500000)/(N*k0);
    const lat=phi-N*t/R*(D*D/2-(5+3*T+10*C-4*C*C-9*ep2)*D**4/24+(61+90*T+298*C+45*T*T-252*ep2-3*C*C)*D**6/720);
    const lon=(D-(1+2*T+C)*D**3/6+(5-2*C+28*T-3*C*C+8*ep2+24*T*T)*D**5/120)/c;
    return [lon/rad-45, lat/rad];
  }
  const side=30/Math.sqrt(3);
  function center(q,r) { return [1.5*side*q,30*(r+q/2)]; }
  function axialAt(x,y) {
    const q=2*x/(3*side), r=(-x/3+Math.sqrt(3)*y/3)/side;
    let u=Math.round(q),v=Math.round(-q-r),w=Math.round(r);
    const du=Math.abs(u-q),dv=Math.abs(v+q+r),dw=Math.abs(w-r);
    if (du>dv && du>dw) u=-v-w;else if (dv>dw) v=-u-w;else w=-u-v;
    return [u,w];
  }
  function axialIndex(array,q,r) {
    let low=0,high=array.length/2;
    while (low<high) { const mid=(low+high)>>>1, x=array[mid*2],y=array[mid*2+1];if (x<q || (x===q && y<r)) low=mid+1;else high=mid; }
    return array[low*2]===q && array[low*2+1]===r ? low : -1;
  }
  function color(value, range, colors) {
    if (!Number.isFinite(value)) return [169,175,180,255];
    const fraction=Math.max(0,Math.min(1,(value-range[0])/(range[1]-range[0] || 1)))*(colors.length-1);
    const i=Math.min(colors.length-2,Math.floor(fraction)),t=fraction-i;
    const from=colors[i],to=colors[i+1];
    return [1,3,5].map(p=>Math.round(parseInt(from.slice(p,p+2),16)*(1-t)+parseInt(to.slice(p,p+2),16)*t)).concat(255);
  }
  function combine(summaries,ras) {
    const selected=ras.length?[...new Set(ras)]:['bacia'];let area=0,valid=0,covered=0,sum=0;
    for (const ra of selected) { const r=summaries[ra];if (!r)continue;area+=r.area_m2;valid+=r.valid_m2;covered+=r.coverage_m2??r.valid_m2;sum+=r.weighted_sum; }
    return { area,valid,mean:valid>0?sum/valid:null,coverage:area>0?100*covered/area:null };
  }
  function csvRecord(id,key,field,value,coverage,unitArea,clippedArea) {
    const available=Number.isFinite(value),state=available?'disponivel':field==='profundidade_media_inundada_m' && coverage>0?'sem_parcela_inundada':'sem_estimativa';
    return [id,key,field,available?value:'',state,coverage,unitArea,clippedArea].join(',')+'\r\n';
  }
  return {utmForward,utmInverse,center,axialAt,axialIndex,color,combine,csvRecord,side};
})();
if (typeof module!=="undefined") module.exports=FitopolisDados;
