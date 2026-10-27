declare module 'virtual:elysia-modules' {
 import {ComponentType} from 'react';
 export const ElysiaPresence: ComponentType<Record<string,unknown>>;
 export const VaultPanel: ComponentType<any>,CodeStudioPanel:ComponentType<any>,WorkspacePanel:ComponentType<any>,WorkbenchPanel:ComponentType<any>,MediaStudioPanel:ComponentType<any>,GenerationPanel:ComponentType<any>,LocalMediaPanel:ComponentType<any>,CapabilitiesPanel:ComponentType<any>;
 export const PALETTES:Record<string,{from:string;to:string;label:string}>;
}
