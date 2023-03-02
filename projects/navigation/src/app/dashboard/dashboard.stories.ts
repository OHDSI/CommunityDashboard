import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { RouterModule } from '@angular/router';
import type { Meta, StoryObj } from '@storybook/angular';
import { moduleMetadata } from '@storybook/angular';
import { DashboardComponent } from './dashboard.component';

const meta: Meta<DashboardComponent> = {
  title: 'CommunityDashboard/Dashboard',
  component: DashboardComponent,
  parameters: {
    layout: 'fullscreen',
  },
  decorators: [
    moduleMetadata({
      imports: [
        DashboardComponent,
        BrowserAnimationsModule,
        RouterModule.forRoot([]),
      ],
    }),
  ],
};

export default meta;
type Story = StoryObj<DashboardComponent>;

export const Component: Story = {
  render: (args: DashboardComponent) => ({
    props: args,
  }),
};
