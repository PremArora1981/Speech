import { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import {
  fetchTelephonyTrunks,
  initiateOutboundCall,
  registerTelephonyTrunk,
  type TelephonyTrunk,
} from '../../lib/api';

export function TelephonyDashboard() {
  const queryClient = useQueryClient();
  const { data: trunks } = useQuery({ queryKey: ['telephony-trunks'], queryFn: fetchTelephonyTrunks });
  const [formState, setFormState] = useState({ trunk_id: '', call_to: '', participant_identity: '', room_name: '' });
  const [trunkForm, setTrunkForm] = useState({ provider: 'livekit', trunk_id: '', direction: 'outbound', sip_uri: '', transport: 'tls', username: '', password: '' });
  const initiateMutation = useMutation({
    mutationFn: async () => {
      await initiateOutboundCall({
        trunk_id: formState.trunk_id,
        call_to: formState.call_to,
        room_name: formState.room_name,
        participant_identity: formState.participant_identity || formState.call_to,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['telephony-trunks'] });
      setFormState(prev => ({ ...prev, call_to: '', participant_identity: '' }));
    },
  });

  const outboundTrunks = useMemo(() => trunks?.filter(trunk => trunk.direction === 'outbound') ?? [], [trunks]);

  const registerMutation = useMutation({
    mutationFn: async () => {
      await registerTelephonyTrunk({
        provider: trunkForm.provider,
        trunk_id: trunkForm.trunk_id,
        direction: trunkForm.direction as 'inbound' | 'outbound',
        sip_uri: trunkForm.sip_uri,
        transport: trunkForm.transport,
        metadata: { label: trunkForm.trunk_id },
        credentials: trunkForm.username && trunkForm.password ? { username: trunkForm.username, password: trunkForm.password } : undefined,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['telephony-trunks'] });
      setTrunkForm(prev => ({ ...prev, trunk_id: '', sip_uri: '', username: '', password: '' }));
    },
  });

  return (
    <div className='space-y-6'>
      <section className='rounded-xl border border-neutral-800 bg-neutral-900/70 p-6'>
        <h2 className='text-lg font-semibold text-neutral-100'>Register Trunk</h2>
        <div className='mt-4 grid gap-4 md:grid-cols-2'>
          <label className='flex flex-col text-sm text-neutral-300'>
            Trunk ID
            <input
              className='mt-1 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2'
              value={trunkForm.trunk_id}
              onChange={event => setTrunkForm(prev => ({ ...prev, trunk_id: event.target.value }))}
              placeholder='ST_xxxx'
            />
          </label>
          <label className='flex flex-col text-sm text-neutral-300'>
            Direction
            <select
              className='mt-1 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2'
              value={trunkForm.direction}
              onChange={event => setTrunkForm(prev => ({ ...prev, direction: event.target.value }))}
            >
              <option value='outbound'>Outbound</option>
              <option value='inbound'>Inbound</option>
            </select>
          </label>
          <label className='flex flex-col text-sm text-neutral-300 md:col-span-2'>
            SIP URI
            <input
              className='mt-1 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2'
              value={trunkForm.sip_uri}
              onChange={event => setTrunkForm(prev => ({ ...prev, sip_uri: event.target.value }))}
              placeholder='sip:sip.provider.com:5061;transport=tls'
            />
          </label>
          <label className='flex flex-col text-sm text-neutral-300'>
            Username (optional)
            <input
              className='mt-1 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2'
              value={trunkForm.username}
              onChange={event => setTrunkForm(prev => ({ ...prev, username: event.target.value }))}
            />
          </label>
          <label className='flex flex-col text-sm text-neutral-300'>
            Password (optional)
            <input
              className='mt-1 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2'
              value={trunkForm.password}
              onChange={event => setTrunkForm(prev => ({ ...prev, password: event.target.value }))}
              type='password'
            />
          </label>
        </div>
        <button
          type='button'
          className='mt-4 rounded-lg bg-sky-500 px-4 py-2 text-sm font-semibold text-neutral-900'
          onClick={() => registerMutation.mutate()}
          disabled={!trunkForm.trunk_id || !trunkForm.sip_uri || registerMutation.isPending}
        >
          {registerMutation.isPending ? 'Saving…' : 'Save Trunk'}
        </button>
      </section>

      <section className='rounded-xl border border-neutral-800 bg-neutral-900/70 p-6'>
        <h2 className='text-lg font-semibold text-neutral-100'>Outbound Call</h2>
        <div className='mt-4 grid grid-cols-1 gap-4 md:grid-cols-2'>
          <label className='flex flex-col text-sm text-neutral-300'>
            Trunk
            <select
              className='mt-1 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2'
              value={formState.trunk_id}
              onChange={event => setFormState(prev => ({ ...prev, trunk_id: event.target.value }))}
            >
              <option value=''>Select trunk…</option>
              {outboundTrunks.map(trunk => (
                <option key={trunk.trunk_id} value={trunk.trunk_id}>
                  {trunk.name} ({trunk.sip_uri})
                </option>
              ))}
            </select>
          </label>
          <label className='flex flex-col text-sm text-neutral-300'>
            Destination Number
            <input
              className='mt-1 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2'
              value={formState.call_to}
              onChange={event => setFormState(prev => ({ ...prev, call_to: event.target.value }))}
              placeholder='+15550001111'
            />
          </label>
          <label className='flex flex-col text-sm text-neutral-300'>
            Participant Identity (optional)
            <input
              className='mt-1 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2'
              value={formState.participant_identity}
              onChange={event => setFormState(prev => ({ ...prev, participant_identity: event.target.value }))}
              placeholder='identity-label'
            />
          </label>
          <label className='flex flex-col text-sm text-neutral-300'>
            Room Name
            <input
              className='mt-1 rounded-lg border border-neutral-700 bg-neutral-950 px-3 py-2'
              value={formState.room_name}
              onChange={event => setFormState(prev => ({ ...prev, room_name: event.target.value }))}
              placeholder='call-1234'
            />
          </label>
        </div>
        <button
          type='button'
          className='mt-4 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-neutral-900'
          onClick={() => initiateMutation.mutate()}
          disabled={!formState.trunk_id || !formState.call_to || !formState.room_name || initiateMutation.isPending}
        >
          {initiateMutation.isPending ? 'Dialing…' : 'Place Call'}
        </button>
      </section>

      <section className='rounded-xl border border-neutral-800 bg-neutral-900/70 p-6'>
        <h2 className='text-lg font-semibold text-neutral-100'>Trunk Inventory</h2>
        <div className='mt-4 grid gap-3'>
          {trunks?.map((trunk: TelephonyTrunk) => (
            <div key={trunk.trunk_id} className='rounded-lg border border-neutral-800 bg-neutral-950/80 p-4'>
              <div className='flex items-center justify-between text-sm text-neutral-300'>
                <span className='font-semibold text-neutral-100'>{trunk.name}</span>
                <span className='uppercase text-xs text-neutral-500'>{trunk.direction}</span>
              </div>
              <div className='mt-2 text-xs text-neutral-400'>
                <div>SIP URI: {trunk.sip_uri}</div>
                <div>Transport: {trunk.transport}</div>
                <div>Trunk ID: {trunk.trunk_id}</div>
              </div>
            </div>
          )) ?? <p className='text-neutral-500'>No trunks found.</p>}
        </div>
      </section>
    </div>
  );
}

