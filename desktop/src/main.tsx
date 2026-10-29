import React from 'react';import {createRoot} from 'react-dom/client';import {setupNativeBridge} from './native';import App from './App';import '../../interface/web/src/elysia.css';import './style.css';import './mobile.css';
setupNativeBridge();
class Boundary extends React.Component<React.PropsWithChildren,{error:string}>{state={error:''};static getDerivedStateFromError(error:Error){return {error:error.message}}render(){return this.state.error?<main style={{padding:40}}><h1>A interface encontrou um problema</h1><p>{this.state.error}</p><button onClick={()=>location.reload()}>Reabrir interface</button></main>:this.props.children}}
createRoot(document.getElementById('root')!).render(<Boundary><App/></Boundary>);
