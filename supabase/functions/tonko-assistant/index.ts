// A public Supabase publishable key identifies the project; it is not user auth.
// Keep verify_jwt=true; browser calls send the publishable key on `apikey`.
// Paid requests are guarded by server-side atomic quotas, not by this public key.
import { createHandler } from './handler.mjs';
import { createKnowledgeLoader } from './knowledge-cache.mjs';
import knowledge from './knowledge.json' with { type: 'json' };

// Created once, outside the request handler, so concurrent requests share refresh.
const knowledgeLoader = createKnowledgeLoader({ embedded: knowledge });
const env = Deno.env.toObject();
Deno.serve(createHandler({ env, knowledge, knowledgeLoader }));
