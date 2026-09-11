import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://xpnyayjzuekduzxlkpim.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'sb_publishable_tB7goht48tnOSBdMPQdmHA_p6IJqFsN';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
