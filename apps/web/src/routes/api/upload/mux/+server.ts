import Mux from '@mux/mux-node';
import { json } from '@sveltejs/kit';
import { MUX_TOKEN_ID, MUX_TOKEN_SECRET } from '$env/static/private';

const mux = new Mux({
    tokenId: MUX_TOKEN_ID,
    tokenSecret: MUX_TOKEN_SECRET
});

export async function POST() {
    try {
        const upload = await mux.video.uploads.create({
            new_asset_settings: {
                playback_policy: ['public'],
                mp4_support: 'standard'
            },
            cors_origin: '*', // In production, lock this down!
        });

        return json({
            id: upload.id,
            url: upload.url
        });
    } catch (error) {
        console.error('Error creating Mux upload:', error);
        return json({ error: 'Error creating upload' }, { status: 500 });
    }
}

export async function GET({ url }) {
    const uploadId = url.searchParams.get('uploadId');
    if (!uploadId) return json({ error: 'Missing uploadId' }, { status: 400 });

    try {
        const upload = await mux.video.uploads.retrieve(uploadId);

        // If asset is created, get its playback ID
        let playbackId = null;
        if (upload.asset_id) {
            const asset = await mux.video.assets.retrieve(upload.asset_id);
            playbackId = asset.playback_ids?.[0]?.id;
        }

        return json({
            status: upload.status,
            assetId: upload.asset_id,
            playbackId: playbackId
        });
    } catch (error) {
        return json({ error: 'Failed to retrieve upload status' }, { status: 500 });
    }
}
