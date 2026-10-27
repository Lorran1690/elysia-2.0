import {defineConfig,transformWithEsbuild} from 'vite';
import react from '@vitejs/plugin-react';
import {readFileSync,cpSync,mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
// Immutable avatar sources are compiled as-is; no iframe, runtime Babel or CDN.
const legacy=['orb-lib.jsx','avatar-rig.js','elysia-presence.jsx','ui-panels.jsx','media-engine.js','modules.jsx','creation.jsx','generation.jsx','workbench.jsx'];
export default defineConfig({plugins:[react(),{name:'preserve-existing-modules',buildStart(){
 mkdirSync('public/assets',{recursive:true});
 for(const n of ['avatar-body.png','avatar-bust-violet.png'])cpSync('../interface/web/assets/'+n,'public/assets/'+n);
 mkdirSync('public/src',{recursive:true});
 for(const n of ['continuous-render.html','continuous-scene.js','continuous-audio.js','continuous-player.js'])cpSync('../interface/web/src/'+n,'public/src/'+n);
 cpSync('../interface/web/vendor/three','public/vendor/three',{recursive:true});
},resolveId(id){if(id==='virtual:elysia-modules')return '\0elysia-modules'},async load(id){if(id!=='\0elysia-modules')return;
 const code="import React from 'react';\n"+legacy.map(n=>readFileSync(resolve('../interface/web/src',n),'utf8')).join('\n;\n')+'\nexport {ElysiaPresence, VaultPanel, CodeStudioPanel, WorkspacePanel, WorkbenchPanel, MediaStudioPanel, GenerationPanel, LocalMediaPanel, CapabilitiesPanel, PALETTES};';
 return (await transformWithEsbuild(code,'legacy.jsx',{loader:'jsx',jsx:'transform',minify:false})).code;
}}],server:{port:1420,strictPort:true,proxy:{'/api':{target:'http://127.0.0.1:8765',changeOrigin:true,configure(proxy){proxy.on('proxyReq',req=>req.removeHeader('origin'))}}}},build:{target:'es2022'},clearScreen:false});
