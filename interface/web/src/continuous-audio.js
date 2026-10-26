/* Original 80 BPM ambient score, synthesized in Web Audio; no recordings or voice. */
export function playScore(context,destination=context.destination) {
  const start=context.currentTime+.1,master=context.createGain(),oscillators=[];
  master.gain.setValueAtTime(0,start);master.gain.linearRampToValueAtTime(.6,start+2);master.gain.setValueAtTime(.6,start+57);master.gain.linearRampToValueAtTime(0,start+60);master.connect(destination);
  const chords=[[50,57,62,65],[46,53,58,62],[48,55,60,64],[45,52,57,60]];
  const note=(at,length,midi,level,pan,pad=false)=>{
    const o=context.createOscillator(),g=context.createGain(),p=context.createStereoPanner();
    o.type=pad?'triangle':'sine';o.frequency.value=440*2**((midi-69)/12);p.pan.value=pan;
    const begin=start+at,end=Math.min(start+60,begin+length);if(end<=begin)return;
    g.gain.setValueAtTime(0,begin);g.gain.linearRampToValueAtTime(level,begin+(pad?.4:.012));g.gain.exponentialRampToValueAtTime(.0001,end);
    o.connect(g);g.connect(p);p.connect(master);o.start(begin);o.stop(end);oscillators.push(o);
    o.onended=()=>{o.disconnect();g.disconnect();p.disconnect();};
  };
  for(let bar=0;bar<20;bar++){
    const chord=chords[bar%4],at=bar*3;
    chord.forEach((midi,i)=>note(at,3.8,midi,.035,(i-1.5)*.35,true));
    for(let n=0;n<8;n++)note(at+n*.375,.7,chord[n%4]+12,.07,Math.sin(n)*.55);
    for(let n=0;n<4;n++)note(at+n*.75,.4,chord[0]-12,.12,0);
  }
  return ()=>{oscillators.forEach(o=>{try{o.stop();}catch{}});master.disconnect();};
}
