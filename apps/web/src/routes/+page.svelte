<script lang="ts">
    import { onMount } from "svelte";
    import "@mux/mux-player";
    import "@mux/mux-uploader";
    import {
        Play,
        Square,
        Settings,
        Upload,
        Music,
        Activity,
        Layers,
        MonitorPlay,
    } from "lucide-svelte";

    // --- MOCK CONSTANTS ---
    const MUX_ENV_KEY = "3sh3p7jontg5rlv7s85ajsbhm"; // From previous context

    // --- TYPES ---
    type ClipStatus = "empty" | "loading" | "ready" | "playing";

    interface Clip {
        id: string;
        name: string;
        status: ClipStatus;
        playbackId?: string;
        bpm?: number;
    }

    interface Layer {
        id: string;
        name: string;
        opacity: number;
        blendMode: "Add" | "Alpha" | "Multiply";
        activeClipId: string | null;
    }

    // --- STATE (Svelte 5 Runes) ---
    let bpm = $state(128.0);
    let isPlaying = $state(false);

    // 4 Layers
    let layers: Layer[] = $state([
        {
            id: "l1",
            name: "Layer 1",
            opacity: 1.0,
            blendMode: "Add",
            activeClipId: null,
        },
        {
            id: "l2",
            name: "Layer 2",
            opacity: 1.0,
            blendMode: "Alpha",
            activeClipId: null,
        },
        {
            id: "l3",
            name: "Layer 3",
            opacity: 0.5,
            blendMode: "Add",
            activeClipId: null,
        },
        {
            id: "l4",
            name: "Layer 4",
            opacity: 0.0,
            blendMode: "Alpha",
            activeClipId: null,
        },
    ]);

    // 4 Rows x 8 Columns Grid
    // Using a flat array logic or matrix. Let's use a Matrix for visual mapping.
    // clips[layerIndex][colIndex]
    let clips: Clip[][] = $state(
        Array(4)
            .fill(null)
            .map((_, lIdx) =>
                Array(8)
                    .fill(null)
                    .map((_, cIdx) => ({
                        id: `clip-${lIdx}-${cIdx}`,
                        name: "",
                        status: "empty",
                    })),
            ),
    );

    let selectedClip: Clip | null = $state(null);
    let fileInput: HTMLInputElement;

    function handleFileSelect(e: Event) {
        const files = (e.target as HTMLInputElement).files;
        if (!files || files.length === 0) return;

        let fileIdx = 0;
        // Reuse the logic to fill empty slots
        for (let l = 0; l < 4; l++) {
            for (let c = 0; c < 8; c++) {
                if (fileIdx >= files.length) break;
                if (clips[l][c].status === "empty") {
                    performUploadAndAnalysis(files[fileIdx], l, c);
                    fileIdx++;
                }
            }
        }
        // Reset input
        (e.target as HTMLInputElement).value = "";
    }

    // --- API & UPLOAD LOGIC ---

    async function triggerAnalysis(
        layerIdx: number,
        colIdx: number,
        playbackId: string,
    ) {
        const clip = clips[layerIdx][colIdx];
        try {
            console.log(`Analyzing clip ${playbackId}...`);
            // Wait for Mux to process a bit?
            // In a real app we would poll Mux status until 'ready'.
            // For now, we assume standard processing takes a moment.

            // Construct MP4 URL (Medium quality is standard)
            const mp4Url = `https://stream.mux.com/${playbackId}/medium.mp4`;

            const res = await fetch("/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: mp4Url }),
            });

            if (!res.ok) throw new Error("Analysis Failed");

            const analysis = await res.json();
            console.log("Essentia Analysis:", analysis);

            // Update Clip with Data
            clip.bpm = analysis.bpm;
            clip.name = clip.name || `Analyzed Clip ${layerIdx}-${colIdx}`;
            // Could store onsets/beats here for visualization
        } catch (e) {
            console.error(e);
        }
    }

    async function performUploadAndAnalysis(
        file: File,
        layerIdx: number,
        colIdx: number,
    ) {
        const clip = clips[layerIdx][colIdx];
        clip.status = "loading";
        clip.name = file.name;

        try {
            // 1. Get Init Upload URL
            const uploadRes = await fetch("/api/upload/mux", {
                method: "POST",
            });
            const { url, id: uploadId } = await uploadRes.json();

            // 2. Upload File to Mux bucket
            await fetch(url, { method: "PUT", body: file });

            // 3. Poll for Playback ID
            // We check status every 2 seconds for up to 60 seconds
            let attempts = 0;
            const maxAttempts = 30;
            let playbackId = null;

            while (attempts < maxAttempts && !playbackId) {
                await new Promise((r) => setTimeout(r, 2000));

                const statusRes = await fetch(
                    `/api/upload/mux?uploadId=${uploadId}`,
                );
                if (statusRes.ok) {
                    const statusData = await statusRes.json();
                    if (statusData.playbackId) {
                        playbackId = statusData.playbackId;
                    }
                }
                attempts++;
            }

            if (playbackId) {
                clip.status = "ready";
                clip.playbackId = playbackId;
                // Trigger analysis once we have the real ID
                triggerAnalysis(layerIdx, colIdx, playbackId);
            } else {
                throw new Error("Upload timed out or processing failed");
            }
        } catch (e) {
            console.error("Upload failed", e);
            clip.status = "empty";
        }
    }

    function handleGlobalDrop(e: DragEvent) {
        e.preventDefault();
        const files = e.dataTransfer?.files;
        if (!files || files.length === 0) return;

        let fileIdx = 0;

        // Find empty slots
        for (let l = 0; l < 4; l++) {
            for (let c = 0; c < 8; c++) {
                if (fileIdx >= files.length) return;

                if (clips[l][c].status === "empty") {
                    performUploadAndAnalysis(files[fileIdx], l, c);
                    fileIdx++;
                }
            }
        }
    }

    // --- ACTIONS ---
    function handleClipClick(layerIdx: number, colIdx: number) {
        const clip = clips[layerIdx][colIdx];
        if (clip.status !== "empty") {
            selectedClip = clip;
            layers[layerIdx].activeClipId = clip.id;
        }
    }
</script>

<div
    class="flex flex-col h-screen w-screen bg-[#1e1e1e] text-gray-300 font-mono overflow-hidden selection:bg-[#ff00eb] selection:text-white"
    ondragover={(e) => e.preventDefault()}
    ondrop={handleGlobalDrop}
    role="application"
>
    <!-- TOP BAR: Transport -->
    <header
        class="h-14 bg-[#121212] border-b border-[#333] flex items-center px-4 justify-between shrink-0"
    >
        <div class="flex items-center gap-4">
            <input
                type="file"
                multiple
                class="hidden"
                accept="video/*,audio/*"
                bind:this={fileInput}
                onchange={handleFileSelect}
            />
            <button
                class="flex items-center gap-2 bg-[#2a2a2a] px-3 py-1 rounded border border-[#444] hover:bg-[#333] hover:border-[#666] transition-colors"
                onclick={() => fileInput.click()}
            >
                <Upload size={14} class="text-[#00ffcc]" />
                <span class="text-xs font-bold text-gray-300">IMPORT</span>
            </button>
            <div
                class="bg-[#2a2a2a] px-3 py-1 rounded border border-[#444] text-[#00ffcc] font-bold"
            >
                {bpm.toFixed(2)} BPM
            </div>
            <button
                class="p-2 hover:bg-[#333] rounded text-white"
                onclick={() => (isPlaying = !isPlaying)}
            >
                {#if isPlaying}
                    <Square size={20} fill="currentColor" />
                {:else}
                    <Play size={20} fill="currentColor" />
                {/if}
            </button>
            <div class="h-8 w-[1px] bg-[#444] mx-2"></div>
            <span
                class="text-xs uppercase tracking-widest font-bold text-[#ff00eb] flex items-center gap-2"
            >
                <MonitorPlay size={16} />
                Muxxy Swap
                <span class="text-[10px] opacity-50">Svelte Engine</span>
            </span>
        </div>

        <!-- Master Control -->
        <div class="flex items-center gap-4">
            <div class="flex flex-col items-end">
                <span class="text-[10px] text-gray-500 uppercase">Master</span>
                <div class="w-32 h-2 bg-[#333] rounded-full overflow-hidden">
                    <div
                        class="h-full bg-gradient-to-r from-[#00ffcc] to-[#ff00eb] w-full"
                    ></div>
                </div>
            </div>
            <Settings
                size={20}
                class="text-gray-500 hover:text-white cursor-pointer"
            />
        </div>
    </header>

    <!-- MAIN WORKSPACE -->
    <div class="flex-1 flex overflow-hidden">
        <!-- LEFT: Layer Controls -->
        <div
            class="w-64 bg-[#181818] border-r border-[#333] flex flex-col shrink-0"
        >
            {#each layers as layer, idx}
                <div
                    class="h-24 border-b border-[#333] p-2 flex flex-col justify-between relative group hover:bg-[#202020] transition-colors"
                >
                    <!-- Header -->
                    <div
                        class="flex justify-between items-center text-xs font-bold text-gray-400"
                    >
                        <span class="flex items-center gap-1"
                            ><Layers size={12} /> {layer.name}</span
                        >
                        <span
                            class="text-[10px] bg-[#222] px-1 rounded uppercase"
                            >{layer.blendMode}</span
                        >
                    </div>

                    <!-- Opacity Slider Mock -->
                    <div
                        class="relative h-2 bg-[#000] rounded overflow-hidden cursor-crosshair group-hover:ring-1 ring-[#555]"
                    >
                        <div
                            class="absolute left-0 top-0 h-full bg-[#ff00eb]"
                            style="width: {layer.opacity * 100}%"
                        ></div>
                    </div>

                    <!-- Controls -->
                    <div class="flex gap-1 mt-1">
                        <button
                            class="bg-[#222] hover:bg-[#333] text-[10px] px-2 py-0.5 rounded text-gray-400"
                            >S</button
                        >
                        <button
                            class="bg-[#222] hover:bg-[#333] text-[10px] px-2 py-0.5 rounded text-gray-400"
                            >M</button
                        >
                        <button
                            class="bg-[#222] hover:bg-[#333] text-[10px] px-2 py-0.5 rounded text-gray-400"
                            >X</button
                        >
                    </div>

                    <!-- Active Indicator -->
                    <div
                        class="absolute left-0 top-0 bottom-0 w-1 bg-[#444] transition-colors"
                        class:bg-[#00ffcc]={layer.activeClipId !== null}
                    ></div>
                </div>
            {/each}
        </div>

        <!-- CENTER: Grid -->
        <div class="flex-1 bg-[#121212] overflow-auto p-2">
            <div
                class="grid grid-cols-8 gap-1 h-full min-w-[800px] auto-rows-[6rem]"
            >
                {#each layers as layer, lIdx}
                    {#each clips[lIdx] as clip, cIdx}
                        <!-- Clip Slot -->
                        <div
                            class="relative border rounded-sm flex items-center justify-center group overflow-hidden transition-all h-24 focus:outline-none focus:ring-2 focus:ring-[#00ffcc]"
                            role="button"
                            tabindex="0"
                            onkeydown={(e) =>
                                (e.key === "Enter" || e.key === " ") &&
                                handleClipClick(lIdx, cIdx)}
                            class:border-[#2a2a2a]={clip.status === "empty"}
                            class:bg-[#1a1a1a]={clip.status === "empty"}
                            class:border-[#ff00eb]={selectedClip === clip}
                            class:ring-1={selectedClip === clip}
                            class:ring-[#ff00eb]={selectedClip === clip}
                            class:border-[#00ffcc]={clip.status === "ready" &&
                                selectedClip !== clip}
                            class:bg-[#2a2a2a]={clip.status !== "empty"}
                        >
                            {#if clip.status === "empty"}
                                <div
                                    class="absolute inset-0 w-full h-full p-1 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center bg-[#1a1a1a]"
                                >
                                    <!-- Mux Uploader Web Component -->
                                    <mux-uploader
                                        endpoint="/api/upload/mux"
                                        class="w-full h-full text-xs"
                                        onsuccess={(e: CustomEvent) => {
                                            console.log(
                                                "Upload success:",
                                                e.detail,
                                            );
                                            clip.status = "loading";
                                            // Wait for asset to process (Simulated delay + Mock ID or Real ID if available)
                                            // In this flow, we will simulate the Mux Processing time
                                            setTimeout(() => {
                                                clip.status = "ready";
                                                clip.name = "New Upload";
                                                // Ideally, we get this from the upload result or webhook.
                                                // Since we don't have it, we use the Demo ID for analysis proof-of-concept
                                                // OR if the user uploads a real file, we would poll for it.
                                                // Using Demo ID to guarantee analysis works for now:
                                                const playbackId =
                                                    "DS00Spx1CV902MCtPj5WknGlR102V5HFkDe";
                                                clip.playbackId = playbackId;

                                                // Trigger Analysis
                                                triggerAnalysis(
                                                    lIdx,
                                                    cIdx,
                                                    playbackId,
                                                );
                                            }, 2000);
                                        }}
                                    >
                                        <div
                                            slot="file-select"
                                            class="flex flex-col items-center justify-center cursor-pointer w-full h-full text-[#555] hover:text-[#ccc]"
                                        >
                                            <Upload size={20} />
                                            <span class="text-[8px] mt-1"
                                                >DROP</span
                                            >
                                        </div>
                                    </mux-uploader>
                                </div>
                                <!-- Fallback Icon when not hovering -->
                                <div
                                    class="flex items-center justify-center pointer-events-none group-hover:opacity-0"
                                >
                                    <div
                                        class="w-2 h-2 rounded-full bg-[#333]"
                                    ></div>
                                </div>
                            {:else if clip.status === "loading"}
                                <Activity
                                    size={20}
                                    class="animate-spin text-[#00ffcc]"
                                />
                            {:else}
                                <!-- Ready Clip -->
                                <button
                                    class="w-full h-full flex flex-col items-center justify-center"
                                    onclick={() => handleClipClick(lIdx, cIdx)}
                                >
                                    <Music
                                        size={16}
                                        class="text-[#00ffcc] mb-1"
                                    />
                                    <span
                                        class="text-[10px] truncate max-w-[90%]"
                                        >{clip.name}</span
                                    >
                                </button>
                                <!-- Playback Indicator -->
                                {#if layer.activeClipId === clip.id}
                                    <div
                                        class="absolute inset-0 border-2 border-[#00ffcc] animate-pulse pointer-events-none"
                                    ></div>
                                {/if}
                            {/if}
                        </div>
                    {/each}
                {/each}
            </div>
        </div>
    </div>

    <!-- BOTTOM: Inspector -->
    <div class="h-48 bg-[#181818] border-t border-[#333] flex shrink-0">
        <div class="w-1/3 border-r border-[#333] p-4">
            <h3
                class="text-xs font-bold text-[#ff00eb] mb-2 flex items-center gap-2"
            >
                <Activity size={14} /> CLIP PROPERTIES
            </h3>
            {#if selectedClip}
                <div class="grid grid-cols-2 gap-4 text-xs">
                    <div>
                        <label class="block text-gray-500 mb-1">
                            Name
                            <input
                                class="w-full bg-[#111] border border-[#333] p-1 text-gray-300 rounded mt-1"
                                bind:value={selectedClip.name}
                            />
                        </label>
                    </div>
                    <div>
                        <label class="block text-gray-500 mb-1">
                            BPM
                            <input
                                class="w-full bg-[#111] border border-[#333] p-1 text-[#00ffcc] rounded mt-1"
                                value={selectedClip.bpm || 128}
                            />
                        </label>
                    </div>
                </div>
            {:else}
                <div class="text-sm text-gray-600 italic mt-4">
                    Select a clip to edit properties
                </div>
            {/if}
        </div>

        <!-- Preview -->
        <div
            class="flex-1 bg-[#000] relative m-2 border border-[#333] rounded overflow-hidden flex items-center justify-center"
        >
            {#if selectedClip?.playbackId}
                <mux-player
                    stream-type="on-demand"
                    playback-id={selectedClip.playbackId}
                    metadata-video-title={selectedClip.name}
                    accent-color="#ff00eb"
                    class="w-full h-full"
                    autoplay
                ></mux-player>
            {:else}
                <div class="opacity-20 flex flex-col items-center gap-2">
                    <Activity size={32} />
                    <span class="text-xs">No Clip Selected</span>
                </div>
            {/if}
        </div>
    </div>
</div>
