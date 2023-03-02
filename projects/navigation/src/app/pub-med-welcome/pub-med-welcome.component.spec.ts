import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PubMedWelcomeComponent } from './pub-med-welcome.component';

describe('PubMedWelcomeComponent', () => {
  let component: PubMedWelcomeComponent;
  let fixture: ComponentFixture<PubMedWelcomeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ PubMedWelcomeComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PubMedWelcomeComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
