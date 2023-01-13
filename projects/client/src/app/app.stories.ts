import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { RouterModule } from '@angular/router';
import type { Meta, StoryObj } from '@storybook/angular';
import { moduleMetadata } from '@storybook/angular';
import { AppComponent } from 'projects/client/src/app/app.component';

const meta: Meta<AppComponent> = {
  title: 'CommunityDashboard/App',
  component: AppComponent,
  parameters: {
    layout: 'fullscreen',
  },
  decorators: [
    moduleMetadata({
      imports: [
        AppComponent,
        BrowserAnimationsModule,
        RouterModule.forRoot([]),
      ],
    }),
  ],
};

export default meta;
type Story = StoryObj<AppComponent>;

export const Component: Story = {
  render: (args: AppComponent) => ({
    props: args,
  }),
};
