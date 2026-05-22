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
    case "blue":
      return "#38bdf8";
    case "gray":
      return "#9ca3af";
    default:
      return fallback ?? "#c6865a";
  }
}

function heatZone(zoneName: string, zones?: FitZone[]): FitZone | undefined {
  return zones?.find((item) => item.zone === zoneName);
}

function heatOpacity(zoneName: string, zones?: FitZone[]): number {
  const zone = heatZone(zoneName, zones);
  if (!zone) return 0;
  if (zone.color === "gray") return 0.28;
  return 0.34 + Math.min(0.08, Math.abs(zone.pressure_score ?? 0) * 0.08);
}

function isTight(zoneName: string, zones?: FitZone[]): boolean {
  const zone = heatZone(zoneName, zones);
  return zone?.status === "apertado" || zone?.color === "red";
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function HatchOverlay(props: { position: [number, number, number]; width: number; height: number }) {
  const offsets = [-0.16, 0, 0.16];
  return (
    <group position={props.position} rotation={[0, 0, -0.62]}>
      {offsets.map((offset) => (
        <mesh key={offset} position={[offset, 0, 0.07]}>
          <boxGeometry args={[0.018, props.height, 0.012]} />
          <meshStandardMaterial color="#1f102f" transparent opacity={0.55} roughness={0.96} />
        </mesh>
      ))}
    </group>
  );
}

function BodyMesh({
  params,
  fitZones,
  rotationY,
}: Props & { rotationY: number }) {
  const color = skinColor(params.skin_tone);

  const chestColor = heatColor("chest", fitZones, color);
  const shoulderColor = heatColor("shoulder", fitZones, color);
  const waistColor = heatColor("waist", fitZones, color);
  const hipColor = heatColor("hip", fitZones, color);
  const bicepsColor = heatColor("biceps", fitZones, color);
  const sleeveColor = heatColor("sleeve", fitZones, bicepsColor);
  const thighColor = heatColor("thigh", fitZones, color);
  const inseamColor = heatColor("inseam", fitZones, thighColor);

  const shoulderWidth = 0.5 * params.shoulder_scale;
  const chestWidth = 1.02 * params.chest_scale;
  const waistWidth = 0.92 * params.waist_scale;
  const hipWidth = 0.68 * params.hip_scale;
  const legScale = clamp(params.leg_scale, 0.88, 1.14);
  const bicepsScale = clamp(params.biceps_scale ?? 1, 0.72, 1.48);
  const thighScale = clamp(params.thigh_scale ?? 1, 0.72, 1.48);
  const chestTight = isTight("chest", fitZones);
  const waistTight = isTight("waist", fitZones);
  const hipTight = isTight("hip", fitZones);
  const bicepsTight = isTight("biceps", fitZones);
  const thighTight = isTight("thigh", fitZones);

  return (
    <group rotation={[0, rotationY, 0]} scale={[0.9, 0.9 * legScale, 0.9]} position={[0, -0.24, 0]}>
      <mesh position={[0, 1.88, 0]} scale={[0.72, 0.96, 0.64]}>
        <sphereGeometry args={[0.2, 44, 32]} />
        <meshStandardMaterial color={color} roughness={0.82} />
      </mesh>

      <mesh position={[0, 1.55, 0]} scale={[1, 1, 0.86]}>
        <capsuleGeometry args={[0.062, 0.24, 12, 28]} />
        <meshStandardMaterial color={color} roughness={0.82} />
      </mesh>

      <mesh position={[-shoulderWidth, 1.38, 0]} scale={[1.02, 0.52, 0.82]}>
        <sphereGeometry args={[0.12, 32, 20]} />
        <meshStandardMaterial color={color} roughness={0.82} />
      </mesh>

      <mesh position={[shoulderWidth, 1.38, 0]} scale={[1.02, 0.52, 0.82]}>
        <sphereGeometry args={[0.12, 32, 20]} />
        <meshStandardMaterial color={color} roughness={0.82} />
      </mesh>
      <mesh position={[-shoulderWidth, 1.38, 0.035]} scale={[1.04, 0.54, 0.84]}>
        <sphereGeometry args={[0.12, 32, 20]} />
        <meshStandardMaterial color={shoulderColor} transparent opacity={heatOpacity("shoulder", fitZones)} roughness={0.9} />
      </mesh>

      <mesh position={[shoulderWidth, 1.38, 0.035]} scale={[1.04, 0.54, 0.84]}>
        <sphereGeometry args={[0.12, 32, 20]} />
        <meshStandardMaterial color={shoulderColor} transparent opacity={heatOpacity("shoulder", fitZones)} roughness={0.9} />
      </mesh>

      <mesh position={[0, 1.12, 0]} scale={[chestWidth, 0.78, 0.54]}>
        <capsuleGeometry args={[0.26, 0.36, 18, 40]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>
      <mesh position={[0, 1.12, 0.018]} scale={[chestWidth * 1.01, 0.79, 0.55]}>
        <capsuleGeometry args={[0.26, 0.36, 18, 40]} />
        <meshStandardMaterial color={chestColor} transparent opacity={heatOpacity("chest", fitZones)} roughness={0.9} />
      </mesh>
      {chestTight ? <HatchOverlay position={[0, 1.12, 0.12]} width={chestWidth} height={0.62} /> : null}

      <mesh position={[0, 0.78, 0]} scale={[waistWidth, 0.76, 0.5]}>
        <capsuleGeometry args={[0.2, 0.18, 16, 36]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>
      <mesh position={[0, 0.78, 0.018]} scale={[waistWidth * 1.01, 0.77, 0.51]}>
        <capsuleGeometry args={[0.2, 0.18, 16, 36]} />
        <meshStandardMaterial color={waistColor} transparent opacity={heatOpacity("waist", fitZones)} roughness={0.9} />
      </mesh>
      {waistTight ? <HatchOverlay position={[0, 0.78, 0.12]} width={waistWidth} height={0.42} /> : null}

      <mesh position={[0, 0.52, 0]} scale={[hipWidth, 0.38, 0.48]}>
        <sphereGeometry args={[0.38, 48, 30]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>
      <mesh position={[0, 0.52, 0.018]} scale={[hipWidth * 1.01, 0.39, 0.49]}>
        <sphereGeometry args={[0.38, 48, 30]} />
        <meshStandardMaterial color={hipColor} transparent opacity={heatOpacity("hip", fitZones)} roughness={0.9} />
      </mesh>
      {hipTight ? <HatchOverlay position={[0, 0.52, 0.13]} width={hipWidth} height={0.48} /> : null}

      <mesh position={[-0.12, 0.34, 0.01]} scale={[1.05 * thighScale, 0.72, 0.9 * thighScale]} rotation={[0, 0, 0.06]}>
        <capsuleGeometry args={[0.088, 0.48, 12, 28]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>

      <mesh position={[0.12, 0.34, 0.01]} scale={[1.05 * thighScale, 0.72, 0.9 * thighScale]} rotation={[0, 0, -0.06]}>
        <capsuleGeometry args={[0.088, 0.48, 12, 28]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>
      <mesh position={[-0.12, 0.34, 0.035]} scale={[1.05 * thighScale, 0.72, 0.9 * thighScale]} rotation={[0, 0, 0.06]}>
        <capsuleGeometry args={[0.088, 0.48, 12, 28]} />
        <meshStandardMaterial color={thighColor} transparent opacity={heatOpacity("thigh", fitZones)} roughness={0.9} />
      </mesh>
      <mesh position={[0.12, 0.34, 0.035]} scale={[1.05 * thighScale, 0.72, 0.9 * thighScale]} rotation={[0, 0, -0.06]}>
        <capsuleGeometry args={[0.088, 0.48, 12, 28]} />
        <meshStandardMaterial color={thighColor} transparent opacity={heatOpacity("thigh", fitZones)} roughness={0.9} />
      </mesh>
      {thighTight ? (
        <>
          <HatchOverlay position={[-0.12, 0.34, 0.13]} width={0.2} height={0.42} />
          <HatchOverlay position={[0.12, 0.34, 0.13]} width={0.2} height={0.42} />
        </>
      ) : null}

      <mesh position={[-0.14 * params.hip_scale, -0.15, 0.01]} scale={[0.9, 1, 0.86]} rotation={[0, 0, 0.03]}>
        <capsuleGeometry args={[0.073, 0.62, 12, 28]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>

      <mesh position={[0.14 * params.hip_scale, -0.15, 0.01]} scale={[0.9, 1, 0.86]} rotation={[0, 0, -0.03]}>
        <capsuleGeometry args={[0.073, 0.62, 12, 28]} />
        <meshStandardMaterial color={color} roughness={0.86} />
      </mesh>

      <mesh position={[-0.14 * params.hip_scale, -0.56, 0.02]} scale={[0.9, 1, 0.82]}>
        <capsuleGeometry args={[0.055, 0.52, 12, 24]} />
        <meshStandardMaterial color={color} roughness={0.86} />
      </mesh>

      <mesh position={[0.14 * params.hip_scale, -0.56, 0.02]} scale={[0.9, 1, 0.82]}>
        <capsuleGeometry args={[0.055, 0.52, 12, 24]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>
      <mesh position={[-0.14 * params.hip_scale, -0.56, 0.035]} scale={[0.9, 1, 0.82]}>
        <capsuleGeometry args={[0.055, 0.52, 12, 24]} />
        <meshStandardMaterial color={inseamColor} transparent opacity={heatOpacity("inseam", fitZones)} roughness={0.9} />
      </mesh>

      <mesh position={[0.14 * params.hip_scale, -0.56, 0.035]} scale={[0.9, 1, 0.82]}>
        <capsuleGeometry args={[0.055, 0.52, 12, 24]} />
        <meshStandardMaterial color={inseamColor} transparent opacity={heatOpacity("inseam", fitZones)} roughness={0.9} />
      </mesh>

      <mesh position={[-shoulderWidth - 0.05, 1.08, 0]} rotation={[0, 0, -0.11]} scale={[0.92 * bicepsScale, 1, 0.86 * bicepsScale]}>
        <capsuleGeometry args={[0.066, 0.46, 12, 28]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>

      <mesh position={[shoulderWidth + 0.05, 1.08, 0]} rotation={[0, 0, 0.11]} scale={[0.92 * bicepsScale, 1, 0.86 * bicepsScale]}>
        <capsuleGeometry args={[0.066, 0.46, 12, 28]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>
      <mesh position={[-shoulderWidth - 0.05, 1.08, 0.035]} rotation={[0, 0, -0.11]} scale={[0.92 * bicepsScale, 1, 0.86 * bicepsScale]}>
        <capsuleGeometry args={[0.066, 0.46, 12, 28]} />
        <meshStandardMaterial color={bicepsColor} transparent opacity={heatOpacity("biceps", fitZones)} roughness={0.9} />
      </mesh>

      <mesh position={[shoulderWidth + 0.05, 1.08, 0.035]} rotation={[0, 0, 0.11]} scale={[0.92 * bicepsScale, 1, 0.86 * bicepsScale]}>
        <capsuleGeometry args={[0.066, 0.46, 12, 28]} />
        <meshStandardMaterial color={bicepsColor} transparent opacity={heatOpacity("biceps", fitZones)} roughness={0.9} />
      </mesh>
      {bicepsTight ? (
        <>
          <HatchOverlay position={[-shoulderWidth - 0.05, 1.08, 0.13]} width={0.16} height={0.34} />
          <HatchOverlay position={[shoulderWidth + 0.05, 1.08, 0.13]} width={0.16} height={0.34} />
        </>
      ) : null}

      <mesh position={[-shoulderWidth - 0.11, 0.72, 0]} rotation={[0, 0, -0.04]} scale={[0.86, 1, 0.82]}>
        <capsuleGeometry args={[0.052, 0.44, 12, 24]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>

      <mesh position={[shoulderWidth + 0.11, 0.72, 0]} rotation={[0, 0, 0.04]} scale={[0.86, 1, 0.82]}>
        <capsuleGeometry args={[0.052, 0.44, 12, 24]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>
      <mesh position={[-shoulderWidth - 0.11, 0.72, 0.035]} rotation={[0, 0, -0.04]} scale={[0.86, 1, 0.82]}>
        <capsuleGeometry args={[0.052, 0.44, 12, 24]} />
        <meshStandardMaterial color={sleeveColor} transparent opacity={heatOpacity("sleeve", fitZones)} roughness={0.9} />
      </mesh>

      <mesh position={[shoulderWidth + 0.11, 0.72, 0.035]} rotation={[0, 0, 0.04]} scale={[0.86, 1, 0.82]}>
        <capsuleGeometry args={[0.052, 0.44, 12, 24]} />
        <meshStandardMaterial color={sleeveColor} transparent opacity={heatOpacity("sleeve", fitZones)} roughness={0.9} />
      </mesh>

      <mesh position={[-shoulderWidth - 0.13, 0.45, 0]} scale={[0.72, 0.92, 0.74]}>
        <sphereGeometry args={[0.055, 24, 16]} />
        <meshStandardMaterial color={color} roughness={0.9} metalness={0.02} />
      </mesh>

      <mesh position={[shoulderWidth + 0.13, 0.45, 0]} scale={[0.72, 0.92, 0.74]}>
        <sphereGeometry args={[0.055, 24, 16]} />
        <meshStandardMaterial color={color} roughness={0.9} metalness={0.02} />
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
      <Canvas camera={{ position: [0, 0.74, 5.2], fov: 41 }}>
        <ambientLight intensity={0.68} />
        <directionalLight position={[2.4, 4.2, 4]} intensity={1.5} />
        <pointLight position={[-2, 1.6, 2.8]} intensity={0.4} />
        <BodyMesh params={params} fitZones={fitZones} rotationY={rotationY} />
      </Canvas>
    </View>
  );
}
