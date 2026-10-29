import {test} from 'node:test';
import assert from 'node:assert/strict';
import {configurePhoneConnection,disconnectPhone,computerRequest} from '../src/phone-connection.ts';
test('remote requests protect credentials and restrict operations',async()=>{
 for(const url of ['http://pc.local','https://user:pass@pc.local','https://pc.local/api','https://pc.local?key=x'])assert.throws(()=>configurePhoneConnection(url,'a'.repeat(43)));
 configurePhoneConnection('https://pc.local','a'.repeat(43));
 let captured;
 const transport=async(...args)=>{captured=args;return new Response('{}')};
 await computerRequest('/api/chat','POST','{"messages":[]}',transport);
 assert.equal(captured[0],'https://pc.local/api/chat');assert.equal(captured[1].redirect,'error');assert.equal(captured[1].credentials,'omit');assert.equal(captured[1].headers.Authorization,'Bearer '+'a'.repeat(43));
 for(const path of ['/api/vault','//attacker.invalid','/api/chat?token=x','/api/generation/file/../0'])await assert.rejects(computerRequest(path,'GET',null,transport));
 disconnectPhone();await assert.rejects(computerRequest('/api/chat','POST','{}',transport));
});
