import {Capacitor} from '@capacitor/core';
export const mobile=import.meta.env.VITE_ELYSIA_MOBILE==='1';
export const androidNative=Capacitor.isNativePlatform()&&Capacitor.getPlatform()==='android';
