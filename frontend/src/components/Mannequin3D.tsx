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
      return "#d9d9d4";
    case "medium":
      return "#c8c8c1";
    case "dark":
      return "#b6b6b0";
    case "deep":
      return "#9d9d98";
    default:
      return "#c8c8c1";
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

function isUnknown(zoneName: string, zones?: FitZone[]): boolean {
  const zone = heatZone(zoneName, zones);
  return zone?.status === "sem_informacao" || zone?.status === "unknown" || zone?.color === "gray";
}

function isRelaxed(zoneName: string, zones?: FitZone[]): boolean {
  const zone = heatZone(zoneName, zones);
  return zone?.status === "folgado" || zone?.status === "loose" || zone?.color === "green" || zone?.color === "blue";
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

function DotOverlay(props: { position: [number, number, number]; width: number; height: number }) {
  const dots = [
    [-0.12, -0.1],
    [0, 0],
    [0.12, 0.1],
  ];

  return (
    <group position={props.position}>
      {dots.map(([x, y]) => (
        <mesh key={`${x}-${y}`} position={[x * props.width, y * props.height, 0.08]}>
          <sphereGeometry args={[0.018, 16, 10]} />
          <meshStandardMaterial color="#f8f3ff" transparent opacity={0.72} roughness={0.96} />
        </mesh>
      ))}
    </group>
  );
}

function DashOverlay(props: { position: [number, number, number]; width: number; height: number }) {
  const offsets = [-0.12, 0.12];

  return (
    <group position={props.position}>
      {offsets.map((offset) => (
        <mesh key={offset} position={[0, offset * props.height, 0.08]}>
          <boxGeometry args={[Math.max(0.12, props.width * 0.26), 0.015, 0.012]} />
          <meshStandardMaterial color="#f8f3ff" transparent opacity={0.48} roughness={0.96} />
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

  const shoulderWidth = 0.42 * params.shoulder_scale;
  const chestWidth = 0.88 * params.chest_scale;
  const waistWidth = 0.66 * params.waist_scale;
  const hipWidth = 0.74 * params.hip_scale;
  const legScale = clamp(params.leg_scale, 0.88, 1.14);
  const bicepsScale = clamp(params.biceps_scale ?? 1, 0.72, 1.48);
  const thighScale = clamp(params.thigh_scale ?? 1, 0.72, 1.48);
  const chestTight = isTight("chest", fitZones);
  const waistTight = isTight("waist", fitZones);
  const hipTight = isTight("hip", fitZones);
  const bicepsTight = isTight("biceps", fitZones);
  const thighTight = isTight("thigh", fitZones);
  const chestUnknown = isUnknown("chest", fitZones);
  const waistUnknown = isUnknown("waist", fitZones);
  const hipUnknown = isUnknown("hip", fitZones);
  const bicepsUnknown = isUnknown("biceps", fitZones);
  const thighUnknown = isUnknown("thigh", fitZones);
  const chestRelaxed = isRelaxed("chest", fitZones);
  const waistRelaxed = isRelaxed("waist", fitZones);
  const hipRelaxed = isRelaxed("hip", fitZones);

  return (
    <group rotation={[0, rotationY, 0]} scale={[0.86, 0.86 * legScale, 0.86]} position={[0, -0.48, 0]}>
      <mesh position={[0, 1.88, 0]} scale={[0.72, 0.96, 0.64]}>
        <sphereGeometry args={[0.2, 44, 32]} />
        <meshStandardMaterial color={color} roughness={0.54} metalness={0.02} />
      </mesh>

      <mesh position={[0, 1.55, 0]} scale={[1, 1, 0.86]}>
        <capsuleGeometry args={[0.062, 0.24, 12, 28]} />
        <meshStandardMaterial color={color} roughness={0.56} metalness={0.02} />
      </mesh>

      <mesh position={[-shoulderWidth, 1.38, 0]} scale={[1.42, 0.58, 0.9]}>
        <sphereGeometry args={[0.12, 32, 20]} />
        <meshStandardMaterial color={color} roughness={0.56} metalness={0.02} />
      </mesh>

      <mesh position={[shoulderWidth, 1.38, 0]} scale={[1.42, 0.58, 0.9]}>
        <sphereGeometry args={[0.12, 32, 20]} />
        <meshStandardMaterial color={color} roughness={0.56} metalness={0.02} />
      </mesh>
      <mesh position={[-shoulderWidth, 1.38, 0.035]} scale={[1.44, 0.60, 0.92]}>
        <sphereGeometry args={[0.12, 32, 20]} />
        <meshStandardMaterial color={shoulderColor} transparent opacity={heatOpacity("shoulder", fitZones)} roughness={0.9} />
      </mesh>

      <mesh position={[shoulderWidth, 1.38, 0.035]} scale={[1.44, 0.60, 0.92]}>
        <sphereGeometry args={[0.12, 32, 20]} />
        <meshStandardMaterial color={shoulderColor} transparent opacity={heatOpacity("shoulder", fitZones)} roughness={0.9} />
      </mesh>

      <mesh position={[0, 1.12, 0]} scale={[chestWidth, 1.12, 0.58]}>
        <sphereGeometry args={[0.42, 64, 34]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>
      <mesh position={[0, 1.12, 0.018]} scale={[chestWidth * 1.01, 1.13, 0.59]}>
        <sphereGeometry args={[0.42, 64, 34]} />
        <meshStandardMaterial color={chestColor} transparent opacity={heatOpacity("chest", fitZones)} roughness={0.9} />
      </mesh>
      {chestTight ? <HatchOverlay position={[0, 1.12, 0.12]} width={chestWidth} height={0.62} /> : null}
      {chestUnknown ? <DotOverlay position={[0, 1.12, 0.12]} width={chestWidth} height={0.62} /> : null}
      {chestRelaxed ? <DashOverlay position={[0, 1.12, 0.12]} width={chestWidth} height={0.62} /> : null}

      <mesh position={[0, 0.80, 0]} scale={[waistWidth, 0.70, 0.50]}>
        <sphereGeometry args={[0.32, 54, 28]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>
      <mesh position={[0, 0.80, 0.018]} scale={[waistWidth * 1.01, 0.71, 0.51]}>
        <sphereGeometry args={[0.32, 54, 28]} />
        <meshStandardMaterial color={waistColor} transparent opacity={heatOpacity("waist", fitZones)} roughness={0.9} />
      </mesh>
      {waistTight ? <HatchOverlay position={[0, 0.78, 0.12]} width={waistWidth} height={0.42} /> : null}
      {waistUnknown ? <DotOverlay position={[0, 0.78, 0.12]} width={waistWidth} height={0.42} /> : null}
      {waistRelaxed ? <DashOverlay position={[0, 0.78, 0.12]} width={waistWidth} height={0.42} /> : null}

      <mesh position={[0, 0.50, 0]} scale={[hipWidth, 0.44, 0.50]}>
        <sphereGeometry args={[0.40, 56, 30]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>
      <mesh position={[0, 0.50, 0.018]} scale={[hipWidth * 1.01, 0.45, 0.51]}>
        <sphereGeometry args={[0.40, 56, 30]} />
        <meshStandardMaterial color={hipColor} transparent opacity={heatOpacity("hip", fitZones)} roughness={0.9} />
      </mesh>
      {hipTight ? <HatchOverlay position={[0, 0.52, 0.13]} width={hipWidth} height={0.48} /> : null}
      {hipUnknown ? <DotOverlay position={[0, 0.52, 0.13]} width={hipWidth} height={0.48} /> : null}
      {hipRelaxed ? <DashOverlay position={[0, 0.52, 0.13]} width={hipWidth} height={0.48} /> : null}

      <mesh position={[-0.11, 0.31, 0.01]} scale={[1.0 * thighScale, 0.82, 0.92 * thighScale]} rotation={[0, 0, 0.045]}>
        <capsuleGeometry args={[0.088, 0.48, 12, 28]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>

      <mesh position={[0.11, 0.31, 0.01]} scale={[1.0 * thighScale, 0.82, 0.92 * thighScale]} rotation={[0, 0, -0.045]}>
        <capsuleGeometry args={[0.088, 0.48, 12, 28]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>
      <mesh position={[-0.11, 0.31, 0.035]} scale={[1.0 * thighScale, 0.82, 0.92 * thighScale]} rotation={[0, 0, 0.045]}>
        <capsuleGeometry args={[0.088, 0.48, 12, 28]} />
        <meshStandardMaterial color={thighColor} transparent opacity={heatOpacity("thigh", fitZones)} roughness={0.9} />
      </mesh>
      <mesh position={[0.11, 0.31, 0.035]} scale={[1.0 * thighScale, 0.82, 0.92 * thighScale]} rotation={[0, 0, -0.045]}>
        <capsuleGeometry args={[0.088, 0.48, 12, 28]} />
        <meshStandardMaterial color={thighColor} transparent opacity={heatOpacity("thigh", fitZones)} roughness={0.9} />
      </mesh>
      {thighTight ? (
        <>
          <HatchOverlay position={[-0.12, 0.34, 0.13]} width={0.2} height={0.42} />
          <HatchOverlay position={[0.12, 0.34, 0.13]} width={0.2} height={0.42} />
        </>
      ) : null}
      {thighUnknown ? (
        <>
          <DotOverlay position={[-0.12, 0.34, 0.13]} width={0.2} height={0.42} />
          <DotOverlay position={[0.12, 0.34, 0.13]} width={0.2} height={0.42} />
        </>
      ) : null}

      <mesh position={[-0.13 * params.hip_scale, -0.16, 0.01]} scale={[0.88, 1.03, 0.84]} rotation={[0, 0, 0.02]}>
        <capsuleGeometry args={[0.073, 0.62, 12, 28]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>

      <mesh position={[0.13 * params.hip_scale, -0.16, 0.01]} scale={[0.88, 1.03, 0.84]} rotation={[0, 0, -0.02]}>
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

      <mesh position={[-shoulderWidth - 0.02, 1.07, 0]} rotation={[0, 0, -0.08]} scale={[0.96 * bicepsScale, 1.03, 0.88 * bicepsScale]}>
        <capsuleGeometry args={[0.066, 0.46, 12, 28]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>

      <mesh position={[shoulderWidth + 0.02, 1.07, 0]} rotation={[0, 0, 0.08]} scale={[0.96 * bicepsScale, 1.03, 0.88 * bicepsScale]}>
        <capsuleGeometry args={[0.066, 0.46, 12, 28]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>
      <mesh position={[-shoulderWidth - 0.02, 1.07, 0.035]} rotation={[0, 0, -0.08]} scale={[0.96 * bicepsScale, 1.03, 0.88 * bicepsScale]}>
        <capsuleGeometry args={[0.066, 0.46, 12, 28]} />
        <meshStandardMaterial color={bicepsColor} transparent opacity={heatOpacity("biceps", fitZones)} roughness={0.9} />
      </mesh>

      <mesh position={[shoulderWidth + 0.02, 1.07, 0.035]} rotation={[0, 0, 0.08]} scale={[0.96 * bicepsScale, 1.03, 0.88 * bicepsScale]}>
        <capsuleGeometry args={[0.066, 0.46, 12, 28]} />
        <meshStandardMaterial color={bicepsColor} transparent opacity={heatOpacity("biceps", fitZones)} roughness={0.9} />
      </mesh>
      {bicepsTight ? (
        <>
          <HatchOverlay position={[-shoulderWidth - 0.02, 1.07, 0.13]} width={0.16} height={0.34} />
          <HatchOverlay position={[shoulderWidth + 0.02, 1.07, 0.13]} width={0.16} height={0.34} />
        </>
      ) : null}
      {bicepsUnknown ? (
        <>
          <DotOverlay position={[-shoulderWidth - 0.02, 1.07, 0.13]} width={0.16} height={0.34} />
          <DotOverlay position={[shoulderWidth + 0.02, 1.07, 0.13]} width={0.16} height={0.34} />
        </>
      ) : null}

      <mesh position={[-shoulderWidth - 0.07, 0.71, 0]} rotation={[0, 0, -0.03]} scale={[0.88, 1, 0.82]}>
        <capsuleGeometry args={[0.052, 0.44, 12, 24]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>

      <mesh position={[shoulderWidth + 0.07, 0.71, 0]} rotation={[0, 0, 0.03]} scale={[0.88, 1, 0.82]}>
        <capsuleGeometry args={[0.052, 0.44, 12, 24]} />
        <meshStandardMaterial color={color} roughness={0.88} metalness={0.02} />
      </mesh>
      <mesh position={[-shoulderWidth - 0.07, 0.71, 0.035]} rotation={[0, 0, -0.03]} scale={[0.88, 1, 0.82]}>
        <capsuleGeometry args={[0.052, 0.44, 12, 24]} />
        <meshStandardMaterial color={sleeveColor} transparent opacity={heatOpacity("sleeve", fitZones)} roughness={0.9} />
      </mesh>

      <mesh position={[shoulderWidth + 0.07, 0.71, 0.035]} rotation={[0, 0, 0.03]} scale={[0.88, 1, 0.82]}>
        <capsuleGeometry args={[0.052, 0.44, 12, 24]} />
        <meshStandardMaterial color={sleeveColor} transparent opacity={heatOpacity("sleeve", fitZones)} roughness={0.9} />
      </mesh>

      <mesh position={[-shoulderWidth - 0.09, 0.43, 0]} scale={[0.72, 0.92, 0.74]}>
        <sphereGeometry args={[0.055, 24, 16]} />
        <meshStandardMaterial color={color} roughness={0.9} metalness={0.02} />
      </mesh>

      <mesh position={[shoulderWidth + 0.09, 0.43, 0]} scale={[0.72, 0.92, 0.74]}>
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
      <Canvas camera={{ position: [0, 0.52, 5.05], fov: 39 }}>
        <ambientLight intensity={0.58} />
        <directionalLight position={[2.2, 4.4, 3.6]} intensity={1.85} />
        <pointLight position={[-2, 1.8, 2.6]} intensity={0.32} />
        <BodyMesh params={params} fitZones={fitZones} rotationY={rotationY} />
      </Canvas>
    </View>
  );
}
