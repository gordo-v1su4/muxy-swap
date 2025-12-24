import { json } from '@sveltejs/kit';
import { ANALYSIS_SERVICE_URL } from '$env/static/private';

export async function POST({ request }) {
    const { url } = await request.json();

    if (!url) {
        return json({ error: 'Missing URL' }, { status: 400 });
    }

    try {
        console.log(`[Proxy] Analyzing audio from: ${url} via ${ANALYSIS_SERVICE_URL}`);

        const response = await fetch(`${ANALYSIS_SERVICE_URL}/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url }),
        });

        if (!response.ok) {
            const err = await response.text();
            throw new Error(`Analysis service error: ${err}`);
        }

        const data = await response.json();
        return json(data);

    } catch (error) {
        console.error('Analysis Proxy Error:', error);
        return json({ error: 'Failed to analyze audio' }, { status: 500 });
    }
}
