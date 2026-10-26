/* Original geometric animation: no photo/video/image inputs or pretrained models. */
import * as THREE from '../vendor/three/three.module.js';
export function createContinuousScene(canvas, width=1280, height=720) {
  const renderer=new THREE.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true});
  renderer.setPixelRatio(1);renderer.setSize(width,height,false);
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;
  const scene=new THREE.Scene();scene.background=new THREE.Color('#050919');scene.fog=new THREE.FogExp2('#050919',.018);
  const camera=new THREE.PerspectiveCamera(47,width/height,.1,160);
  scene.add(new THREE.HemisphereLight(0xabcfff,0x141126,2));
  const key=new THREE.DirectionalLight(0xc7dfff,3);key.position.set(5,12,8);scene.add(key);
  const rim=new THREE.DirectionalLight(0xc68aff,3);rim.position.set(-8,5,-8);scene.add(rim);
  const materials=[];
  const material=(color,metal=.4,emission=0)=>{const m=new THREE.MeshStandardMaterial({color,metalness:metal,roughness:.3,emissive:color,emissiveIntensity:emission});materials.push(m);return m;};
  const dark=material(0x14223f,.75),silver=material(0xc4d4ea,.65),purple=material(0xa878ff,.4,.7),cyan=material(0x54e1ff,.3,.9),pink=material(0xff78cb,.3,.7);
  const mesh=(geometry,mat,parent=scene,x=0,y=0,z=0)=>{const o=new THREE.Mesh(geometry,mat);o.position.set(x,y,z);parent.add(o);return o;};
  const sphere=(radius,mat,parent,x=0,y=0,z=0)=>mesh(new THREE.SphereGeometry(radius,24,16),mat,parent,x,y,z);
  const box=(x,y,z,mat,parent,px=0,py=0,pz=0)=>mesh(new THREE.BoxGeometry(x,y,z),mat,parent,px,py,pz);
  const ring=(radius,thickness,mat,parent,x=0,y=0,z=0)=>mesh(new THREE.TorusGeometry(radius,thickness,8,64),mat,parent,x,y,z);
  const cylinder=(r,h,mat,parent,x=0,y=0,z=0)=>mesh(new THREE.CylinderGeometry(r,r,h,48),mat,parent,x,y,z);
  const floor=cylinder(22,.2,dark,scene,0,-.22,0);
  const grid=new THREE.GridHelper(48,48,0x4b5889,0x142540);grid.position.y=-.1;scene.add(grid);
  for(let r=3;r<21;r+=3){const o=ring(r,.018,r%2?purple:cyan,scene,0,-.08,0);o.rotation.x=Math.PI/2;}
  // Standing stylized robotic avatar, built entirely from geometry.
  const avatar=new THREE.Group();scene.add(avatar);avatar.position.y=.25;
  cylinder(1.9,.35,dark,avatar);const base=ring(1.8,.06,cyan,avatar,0,.22);base.rotation.x=Math.PI/2;
  const torso=mesh(new THREE.CapsuleGeometry(.62,1.05,8,24),silver,avatar,0,2.9,0);torso.scale.z=.58;
  const waist=sphere(.47,dark,avatar,0,2.05,0);waist.scale.set(1,.8,.7);
  const chest=ring(.26,.045,purple,avatar,0,3.15,.4);
  for(const side of [-1,1]){
    const leg=mesh(new THREE.CapsuleGeometry(.22,1.15,6,16),silver,avatar,side*.33,1.18,0);leg.rotation.z=side*-.06;
    box(.4,.22,.8,dark,avatar,side*.38,.31,.16);
    sphere(.23,purple,avatar,side*.36,1.25,.18);
  }
  cylinder(.2,.3,dark,avatar,0,3.85,0);
  const head=new THREE.Group();avatar.add(head);head.position.y=4.4;
  const skull=sphere(.62,silver,head);skull.scale.set(.85,1.15,.82);
  const face=sphere(.54,dark,head,0,0,.22);face.scale.set(.86,.68,.64);
  for(const side of [-1,1]){const eye=box(.23,.065,.08,cyan,head,side*.21,.05,.58);eye.rotation.z=-side*.1;sphere(.16,purple,head,side*.54,0,0);}
  const arms=[];
  for(const side of [-1,1]){
    const arm=new THREE.Group();avatar.add(arm);arm.position.set(side*.76,3.42,0);
    sphere(.23,dark,arm);const upper=mesh(new THREE.CapsuleGeometry(.15,.7,6,12),silver,arm,side*.26,-.4,0);upper.rotation.z=side*.55;
    const fore=new THREE.Group();arm.add(fore);fore.position.set(side*.5,-.8,0);sphere(.17,purple,fore);
    const lower=mesh(new THREE.CapsuleGeometry(.13,.65,6,12),silver,fore,0,-.38,.24);lower.rotation.x=-.55;
    sphere(.18,silver,fore,0,-.72,.46);arms.push({arm,fore,side});
  }
  const core=new THREE.Group();scene.add(core);core.position.set(0,3.8,2.2);
  const nucleus=mesh(new THREE.IcosahedronGeometry(.58,2),purple,core);
  const cage=mesh(new THREE.IcosahedronGeometry(.72,1),new THREE.MeshBasicMaterial({color:0x8fffff,wireframe:true}),core);
  const orbits=[];for(let i=0;i<3;i++){const o=ring(1+i*.12,.024,i===1?purple:cyan,core);orbits.push(o);}
  // Modules are physical stations in the same space; the camera never cuts.
  const labels=[],stations=[],pulses=[],nodes=[];
  function label(text,sub,parent,y=2.5) {
    const c=document.createElement('canvas');c.width=1024;c.height=256;const ctx=c.getContext('2d');
    ctx.fillStyle='rgba(5,12,32,.5)';ctx.fillRect(0,0,1024,256);ctx.fillStyle='#72eaff';ctx.fillRect(0,0,1024,5);
    ctx.textAlign='center';ctx.fillStyle='#ffffff';ctx.font='600 64px sans-serif';ctx.fillText(text,512,108,990);
    ctx.font='32px sans-serif';ctx.fillStyle='#b4c6e7';ctx.fillText(sub,512,180,990);
    const texture=new THREE.CanvasTexture(c);texture.colorSpace=THREE.SRGBColorSpace;
    const mat=new THREE.SpriteMaterial({map:texture,transparent:true,depthWrite:false});
    const sprite=new THREE.Sprite(mat);sprite.position.y=y;sprite.scale.set(3.8,.95,1);parent.add(sprite);labels.push(sprite);return sprite;
  }
  const title=new THREE.Group();title.position.set(0,6.2,0);scene.add(title);label('E.L.Y.S.I.A.','Um universo em construção',title,0);
  const definitions=[['NEURAL CORE','Pesquisa de linguagem própria'],['CONHECIMENTO','Notas e busca local'],['MEDIA STUDIO','Ferramentas de criação'],['CÓDIGO','Editor e validação'],['BACKUP PRIVADO','Preservar suas ideias'],['EVOLUÇÃO','Projeto versionado no GitHub']];
  definitions.forEach(([name,sub],i)=>{
    const a=i*Math.PI/3,g=new THREE.Group();g.position.set(Math.cos(a)*8,0,Math.sin(a)*8);scene.add(g);stations.push(g);
    cylinder(1.55,.35,dark,g,0,.1);const border=ring(1.5,.045,i%2?purple:cyan,g,0,.3);border.rotation.x=Math.PI/2;
    label(name,sub,g,3.45);
    if(i===0){for(let n=0;n<15;n++){const angle=n*2.4,r=.4+(n%3)*.3;const node=sphere(.09,n%2?purple:cyan,g,Math.cos(angle)*r,1.3+Math.sin(n)*.65,Math.sin(angle)*r);nodes.push({node,base:node.position.clone(),i:n});}
      const positions=[];for(let n=0;n<nodes.length;n++)for(let m=n+1;m<nodes.length;m++)if((n+m)%4===0){positions.push(...nodes[n].base.toArray(),...nodes[m].base.toArray());}
      const geom=new THREE.BufferGeometry();geom.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.add(new THREE.LineSegments(geom,new THREE.LineBasicMaterial({color:0x6c78c8,transparent:true,opacity:.6})));
    }else if(i===1||i===4){for(let n=0;n<6;n++)box(1.3,.12,.9,n%2?purple:cyan,g,0,.7+n*.25,0);}
    else if(i===2){const art=mesh(new THREE.TorusKnotGeometry(.58,.16,64,8),pink,g,0,1.6,0);g.userData.art=art;}
    else if(i===3){for(let n=0;n<10;n++)box(.4+(n%4)*.18,.08,.08,n%2?cyan:purple,g,((n%3)-1)*.1,.65+n*.19,0);}
    else {g.userData.art=mesh(new THREE.OctahedronGeometry(.85),cyan,g,0,1.5,0);}
    const start=new THREE.Vector3(0,1.4,0),end=g.position.clone().setY(.35);
    const mid=start.clone().lerp(end,.5);mid.y=3;
    const curve=new THREE.QuadraticBezierCurve3(start,mid,end);
    mesh(new THREE.TubeGeometry(curve,24,.014,4,false),material(i%2?0x8462d8:0x278fae,.2,.5));
    for(let n=0;n<4;n++){const dot=sphere(.075,i%2?purple:cyan,scene);pulses.push({dot,curve,phase:n/4+i*.12});}
  });
  // Architectural ribs and stars supply parallax and depth during the travelling shot.
  for(let i=0;i<18;i++){const a=i*Math.PI/9;const p=box(.12,8,.12,dark,scene,Math.cos(a)*17,3.8,Math.sin(a)*17);const strip=box(.028,7.5,.13,i%2?cyan:purple,scene,p.position.x,3.8,p.position.z);}
  const starPositions=[];for(let i=0;i<230;i++){const a=i*2.39996,r=20+(i%11)*2;starPositions.push(Math.cos(a)*r,3+(i%17)*.8,Math.sin(a)*r);}
  const starsGeo=new THREE.BufferGeometry();starsGeo.setAttribute('position',new THREE.Float32BufferAttribute(starPositions,3));scene.add(new THREE.Points(starsGeo,new THREE.PointsMaterial({color:0xa9c6ff,size:.055})));
  function render(seconds) {
    const t=Math.max(0,Math.min(60,seconds)),a=Math.PI/2+t/60*Math.PI*2;
    const distance=19-1.5*Math.sin(Math.PI*t/60)**2;
    camera.position.set(Math.cos(a)*distance,7+1.2*Math.sin(t/12),Math.sin(a)*distance);camera.lookAt(0,2.8,0);
    avatar.rotation.y=a-Math.PI/2;head.rotation.y=.2*Math.sin(t*.7);head.rotation.z=.04*Math.sin(t*.5);avatar.position.y=.25+.06*Math.sin(t*1.4);
    arms.forEach(({arm,fore,side})=>{arm.rotation.x=-.18+.15*Math.sin(t*.7+side);arm.rotation.z=side*(.14+.1*Math.sin(t*.7));fore.rotation.x=-.25+.14*Math.sin(t*.7+side);});
    core.position.y=3.4+.2*Math.sin(t*1.2);nucleus.rotation.set(t*.3,t*.6,0);nucleus.scale.setScalar(1+.08*Math.sin(t*2));cage.rotation.set(-t*.2,t*.35,t*.2);
    orbits.forEach((o,i)=>o.rotation.set(t*.3+i,t*.2+i*.9,t*.12));
    stations.forEach((g,i)=>{if(g.userData.art)g.userData.art.rotation.set(t*.4,t*.5,0);if(i===1||i===4)g.rotation.y=.12*Math.sin(t*.5);});
    nodes.forEach(({node,i})=>node.scale.setScalar(.8+.4*Math.sin(t*2+i)));
    pulses.forEach(({dot,curve,phase})=>dot.position.copy(curve.getPoint((t*.17+phase)%1)));
    renderer.render(scene,camera);
    return {camera:camera.position.toArray(),time:t,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles};
  }
  function dispose(){scene.traverse(o=>{o.geometry?.dispose();const list=Array.isArray(o.material)?o.material:[o.material];list.forEach(m=>{m?.map?.dispose();m?.dispose();});});renderer.dispose();}
  return {render,dispose,renderer};
}
