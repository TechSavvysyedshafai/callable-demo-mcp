import React from 'react';
import {Composition} from 'remotion';
import {Story} from './Story';
export const Root: React.FC = () => (
  <Composition id="Story" component={Story} width={1080} height={1920} fps={30} durationInFrames={58 * 30} />
);
