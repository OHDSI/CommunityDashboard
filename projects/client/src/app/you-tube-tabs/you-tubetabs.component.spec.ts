import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { YouTubeTabsComponent } from './you-tube-tabs.component';

describe('YouTubeTabsComponent', () => {
  let component: YouTubeTabsComponent;
  let fixture: ComponentFixture<YouTubeTabsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ 
        YouTubeTabsComponent,
        NoopAnimationsModule,
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(YouTubeTabsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
