import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';

import { PubMedSummaryComponent } from './pub-med-summary.component';

describe('PubMedSummaryComponent', () => {
  let component: PubMedSummaryComponent;
  let fixture: ComponentFixture<PubMedSummaryComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        PubMedSummaryComponent,
        RouterTestingModule,
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PubMedSummaryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
