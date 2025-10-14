import axios from 'axios';

import { appConfig } from './config';

export type TelephonyTrunk = {
  trunk_id: string;
  name: string;
  direction: 'inbound' | 'outbound';
  sip_uri: string;
  transport: string;
};

export async function fetchTelephonyTrunks(): Promise<TelephonyTrunk[]> {
  const response = await axios.get(`${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/telephony/trunks`, {
    headers: { 'X-API-Key': appConfig.apiKey },
  });
  return response.data.trunks as TelephonyTrunk[];
}

export async function registerTelephonyTrunk(payload: {
  provider: string;
  trunk_id: string;
  direction: 'inbound' | 'outbound';
  sip_uri: string;
  transport?: string;
  metadata?: Record<string, unknown>;
  credentials?: Record<string, string>;
}) {
  await axios.post(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/telephony/trunks`,
    payload,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
    },
  );
}

export async function initiateOutboundCall(payload: {
  trunk_id: string;
  call_to: string;
  participant_identity?: string;
  room_name: string;
  wait_until_answered?: boolean;
}) {
  await axios.post(
    `${appConfig.restTtsUrl.replace('/api/v1/tts', '')}/api/v1/telephony/calls`,
    payload,
    {
      headers: { 'X-API-Key': appConfig.apiKey },
    },
  );
}

