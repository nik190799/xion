/**
 * Client-side cryptographic operations for Phase 6.3.b.
 * 
 * Generates an Ed25519 keypair via the Web Crypto API, stores the private key
 * non-extractably in IndexedDB, and exposes a signMessage helper.
 */

const DB_NAME = 'xion_crypto_db';
const STORE_NAME = 'keys';

// Phase 6.4: Cross-tab key wipe sync
const keyChannel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel('xion:keys') : null;

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
    request.onsuccess = (event) => resolve((event.target as IDBOpenDBRequest).result);
    request.onerror = (event) => reject((event.target as IDBOpenDBRequest).error);
  });
}

export async function getOrGenerateKeypair(): Promise<{ publicKeyB64: string; privateKey: CryptoKey }> {
  const db = await openDB();
  
  return new Promise(async (resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    
    const getReq = store.get('ed25519_keypair');
    getReq.onsuccess = async () => {
      if (getReq.result) {
        resolve(getReq.result);
      } else {
        try {
          const keyPair = await window.crypto.subtle.generateKey(
            'Ed25519',
            false, // non-extractable private key
            ['sign', 'verify']
          );
          
          const exportedPub = await window.crypto.subtle.exportKey('raw', keyPair.publicKey);
          const publicKeyB64 = btoa(String.fromCharCode(...new Uint8Array(exportedPub)));
          
          const result = { publicKeyB64, privateKey: keyPair.privateKey };
          const putReq = store.put(result, 'ed25519_keypair');
          putReq.onsuccess = () => resolve(result);
          putReq.onerror = (err) => reject(err);
        } catch (e) {
          reject(e);
        }
      }
    };
    getReq.onerror = (err) => reject(err);
  });
}

export async function signMessage(message: string): Promise<{ signatureB64: string; publicKeyB64: string }> {
  const { publicKeyB64, privateKey } = await getOrGenerateKeypair();
  
  const payload = new TextEncoder().encode(`${publicKeyB64}|${message}`);
  const signatureBuffer = await window.crypto.subtle.sign(
    'Ed25519',
    privateKey,
    payload
  );
  
  const signatureB64 = btoa(String.fromCharCode(...new Uint8Array(signatureBuffer)));
  return { signatureB64, publicKeyB64 };
}

export async function forgetKeys(): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    const clearReq = store.clear();
    clearReq.onsuccess = () => {
      keyChannel?.postMessage({ type: 'forgotten' });
      resolve();
    };
    clearReq.onerror = (err) => reject(err);
  });
}
