import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';

import { YouTubeSummaryComponent } from './you-tube-summary.component';

describe('YouTubeSummaryComponent', () => {
  let component: YouTubeSummaryComponent;
  let fixture: ComponentFixture<YouTubeSummaryComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ 
        YouTubeSummaryComponent,
        RouterTestingModule,
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(YouTubeSummaryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
