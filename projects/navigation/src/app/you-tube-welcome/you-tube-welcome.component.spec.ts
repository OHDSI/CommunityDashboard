import { ComponentFixture, TestBed } from '@angular/core/testing';

import { YouTubeWelcomeComponent } from './you-tube-welcome.component';

describe('PubMedWelcomeComponent', () => {
  let component: YouTubeWelcomeComponent;
  let fixture: ComponentFixture<YouTubeWelcomeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ YouTubeWelcomeComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(YouTubeWelcomeComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
