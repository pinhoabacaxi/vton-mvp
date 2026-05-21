import React, { useMemo, useRef, useState } from "react";
import { PanResponder, View } from "react-native";
import { Canvas } from "@react-three/fiber/native";
import { MannequinParams } from "../types/body";
import { FitZone } from "../types/product";

type Props = {
  params: MannequinParams;
  fitZones?: FitZone[];
};

function skinColor(tone: string): string {
  switch (tone) {
    case "light":
      return "#f2c7a5";
    case "medium":
      return "#c6865a";
    case "dark":
      return "#6b3f2a";
    case "deep":
      return "#3a241c";
    default:
      return "#c6865a";
  }
}

function heatColor(zoneName: string, zones?: FitZone[], fallback?: string): string {
  const zone = zones?.find((item) => item.zone === zoneName);

  if (!zone) {
    return fallback ?? "#c6865a";
  }

  switch (zone.color) {
    case "red":
      return "#ef4444";
    case "yellow":
      return "#facc15";
    case "green":
      return "#22c55e";
    case "gray":
      return "#9ca3af";
    default:
      return fallback ?? "#c6865a";
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function BodyMesh({
  params,
  fitZones,
  rotationY,
}: Props & { rotationY: number }) {
  const color = skinColor(params.skin_tone);

  const chestColor = heatColor("chest", fitZones, color);
  const waistColor = heatColor("waist", fitZones, color);
  const hipColor = heatColor("hip", fitZones, color);

  const showHeatmap = Boolean(fitZones && fitZones.length > 0);

  return (
    <group rotation={[0, rotationY, 0]} scale={[1, params.leg_scale, 1]}>
      <mesh position={[0, 1.85, 0]}>
        <sphereGeometry args={[0.22, 32, 32]} />
        <meshStandardMaterial color={color} />
      </mesh>

      <mesh position={[0, 1.35, 0]} scale={[params.shoulder_scale, 1, 0.55]}>
        <boxGeometry args={[0.75, 0.55, 0.35]} />
        <meshStandardMaterial color={showHeatmap ? chestColor : color} />
      </mesh>

      <mesh position={[0, 0.95, 0]} scale={[params.waist_scale, 1, 0.5]}>
        <boxGeometry args={[0.48, 0.38, 0.32]} />
        <meshStandardMaterial color={showHeatmap ? waistColor : color} />
      </mesh>

      <mesh position={[0, 0.58, 0]} scale={[params.hip_scale, 1, 0.55]}>
        <boxGeometry args={[0.7, 0.38, 0.35]} />
        <meshStandardMaterial color={showHeatmap ? hipColor : color} />
      </mesh>

      <mesh position={[-0.55 * params.shoulder_scale, 1.05, 0]} rotation={[0, 0, -0.18]}>
        <capsuleGeometry args={[0.08, 0.75, 8, 16]} />
        <meshStandardMaterial color={color} />
      </mesh>

      <mesh position={[0.55 * params.shoulder_scale, 1.05, 0]} rotation={[0, 0, 0.18]}>
        <capsuleGeometry args={[0.08, 0.75, 8, 16]} />
        <meshStandardMaterial color={color} />
      </mesh>

      <mesh position={[-0.18 * params.hip_scale, 0.0, 0]}>
        <capsuleGeometry args={[0.1, 0.95, 8, 16]} />
        <meshStandardMaterial color={color} />
      </mesh>

      <mesh position={[0.18 * params.hip_scale, 0.0, 0]}>
        <capsuleGeometry args={[0.1, 0.95, 8, 16]} />
        <meshStandardMaterial color={color} />
      </mesh>
    </group>
  );
}

export function Mannequin3D({ params, fitZones }: Props) {
  const [rotationY, setRotationY] = useState(0);
  const rotationRef = useRef(0);
  const gestureStartRef = useRef(0);

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => true,
        onMoveShouldSetPanResponder: (_, gesture) => Math.abs(gesture.dx) > 4,
        onPanResponderGrant: () => {
          gestureStartRef.current = rotationRef.current;
        },
        onPanResponderMove: (_, gesture) => {
          const nextRotation = clamp(
            gestureStartRef.current + gesture.dx / 280,
            -0.55,
            0.55
          );
          rotationRef.current = nextRotation;
          setRotationY(nextRotation);
        },
        onPanResponderRelease: () => {
          gestureStartRef.current = rotationRef.current;
        },
        onPanResponderTerminate: () => {
          gestureStartRef.current = rotationRef.current;
        },
      }),
    []
  );

  return (
    <View
      {...panResponder.panHandlers}
      style={{ height: 420, width: "100%", borderRadius: 24, overflow: "hidden" }}
    >
      <Canvas camera={{ position: [0, 1.1, 4], fov: 45 }}>
        <ambientLight intensity={0.8} />
        <directionalLight position={[2, 4, 4]} intensity={1.4} />
        <BodyMesh params={params} fitZones={fitZones} rotationY={rotationY} />
      </Canvas>
    </View>
  );
}
