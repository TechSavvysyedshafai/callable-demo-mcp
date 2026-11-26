import React from 'react';
import {Composition} from 'remotion';
import {Ad} from './Ad';
export const Root: React.FC = () => (<Composition id="Ad" component={Ad} width={1080} height={1920} fps={30} durationInFrames={20 * 30} />);
