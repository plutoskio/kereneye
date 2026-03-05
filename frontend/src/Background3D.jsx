import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const ParticleNetwork = ({ count = 400 }) => {
    const pointsRef = useRef();
    const linesRef = useRef();

    // Generate random points in a 3D sphere
    const [positions, colors] = useMemo(() => {
        const pos = new Float32Array(count * 3);
        const cols = new Float32Array(count * 3);
        const colorGen = new THREE.Color();

        for (let i = 0; i < count; i++) {
            const radius = 25 * Math.random();
            const theta = Math.random() * 2 * Math.PI;
            const phi = Math.acos((Math.random() * 2) - 1);

            pos[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
            pos[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
            pos[i * 3 + 2] = radius * Math.cos(phi);

            // Subtle Altruist Gray / Blue blend
            colorGen.setHSL(0.58 + Math.random() * 0.05, 0.4, 0.4 + Math.random() * 0.2);
            cols[i * 3] = colorGen.r;
            cols[i * 3 + 1] = colorGen.g;
            cols[i * 3 + 2] = colorGen.b;
        }
        return [pos, cols];
    }, [count]);

    // Create connecting lines based on distance
    const linePositions = useMemo(() => {
        const lines = [];
        const maxDist = 4.5;
        for (let i = 0; i < count; i++) {
            for (let j = i + 1; j < count; j++) {
                const dx = positions[i * 3] - positions[j * 3];
                const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
                const dz = positions[i * 3 + 2] - positions[j * 3 + 2];
                const distSq = dx * dx + dy * dy + dz * dz;

                if (distSq < maxDist * maxDist) {
                    lines.push(
                        positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2],
                        positions[j * 3], positions[j * 3 + 1], positions[j * 3 + 2]
                    );
                }
            }
        }
        return new Float32Array(lines);
    }, [positions, count]);

    useFrame((state) => {
        const t = state.clock.getElapsedTime();
        // Gentle floating rotation
        if (pointsRef.current) {
            pointsRef.current.rotation.y = t * 0.05;
            pointsRef.current.rotation.x = Math.sin(t * 0.1) * 0.1;
        }
        if (linesRef.current) {
            linesRef.current.rotation.y = t * 0.05;
            linesRef.current.rotation.x = Math.sin(t * 0.1) * 0.1;
        }

        // Parallax mouse effect
        const mouseX = (state.pointer.x * Math.PI) / 10;
        const mouseY = (state.pointer.y * Math.PI) / 10;
        state.camera.position.x += (mouseX - state.camera.position.x) * 0.05;
        state.camera.position.y += (-mouseY - state.camera.position.y) * 0.05;
        state.camera.lookAt(0, 0, 0);
    });

    return (
        <>
            <points ref={pointsRef}>
                <bufferGeometry>
                    <bufferAttribute attach="attributes-position" count={positions.length / 3} array={positions} itemSize={3} />
                    <bufferAttribute attach="attributes-color" count={colors.length / 3} array={colors} itemSize={3} />
                </bufferGeometry>
                <pointsMaterial size={0.06} vertexColors transparent opacity={0.6} sizeAttenuation={true} />
            </points>
            <lineSegments ref={linesRef}>
                <bufferGeometry>
                    <bufferAttribute attach="attributes-position" count={linePositions.length / 3} array={linePositions} itemSize={3} />
                </bufferGeometry>
                <lineBasicMaterial color="#E5E7EB" transparent opacity={0.15} />
            </lineSegments>
        </>
    );
};

export default function Background3D() {
    return (
        <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden bg-altruistGray-50">
            <Canvas camera={{ position: [0, 0, 20], fov: 60 }} dpr={[1, 2]}>
                <color attach="background" args={['#F9FAFB']} />
                <ambientLight intensity={0.5} />
                <ParticleNetwork count={500} />
            </Canvas>
            {/* Soft vignette overlay */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#F9FAFB_80%)] pointer-events-none" />
        </div>
    );
}
